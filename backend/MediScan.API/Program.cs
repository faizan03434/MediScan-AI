using System.Text;
using MediScan.API.Middleware;
using MediScan.Core.Entities;
using MediScan.Core.Interfaces;
using MediScan.Core.Services;
using MediScan.Infra.Data;
using MediScan.Infra.External;
using MediScan.Infra.Repositories;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;
using Microsoft.OpenApi.Models;
using Serilog;
using MediScan.API.Services;
using System.Threading.RateLimiting;
using Microsoft.AspNetCore.RateLimiting;
using Microsoft.AspNetCore.DataProtection;
using System.Security.Cryptography.X509Certificates;
using MediScan.Operations;
using MediScan.Operations.Privacy;

// ─────────────────────────────────────────────
// Bootstrap Serilog early
// ─────────────────────────────────────────────
Log.Logger = new LoggerConfiguration()
    .WriteTo.Console()
    .CreateBootstrapLogger();

try
{
    var initializeDatabase = args.Contains("--initialize-database");
    var builder = WebApplication.CreateBuilder(args.Where(a => a != "--initialize-database").ToArray());
    // Local secrets are deliberately excluded from version control. Environment overrides win.
    builder.Configuration.AddJsonFile("appsettings.Local.json", optional: true, reloadOnChange: true)
        .AddInMemoryCollection(EnvFileConfiguration.Read(Path.Combine(builder.Environment.ContentRootPath, ".env")))
        .AddEnvironmentVariables();
    if (!builder.Environment.IsDevelopment()) ProductionConfiguration.Validate(builder.Configuration);
    using var runtimeLease = initializeDatabase ? RuntimeLease.Maintenance(builder.Environment.ContentRootPath)
        : RuntimeLease.Shared(builder.Environment.ContentRootPath);

    // ─── Serilog ───────────────────────────────
    builder.Host.UseSerilog((ctx, lc) => lc
        .ReadFrom.Configuration(ctx.Configuration)
        .WriteTo.Console());

    // ─── Database ──────────────────────────────
    // Auto-select: SQLite for dev (no PostgreSQL password needed), PostgreSQL for prod
    var connStr = builder.Configuration.GetConnectionString("DefaultConnection") ?? "";
    builder.Services.AddDbContext<AppDbContext>(options =>
    {
        DatabaseOptions.Configure(options, connStr, builder.Configuration["Database:Provider"], builder.Environment.ContentRootPath);
    });

    // ─── Identity ──────────────────────────────
    builder.Services.AddIdentity<ApplicationUser, IdentityRole>(options =>
    {
        options.Password.RequiredLength = 8;
        options.Password.RequireNonAlphanumeric = false;
        options.Password.RequireUppercase = true;
        options.Password.RequireDigit = true;
        options.User.RequireUniqueEmail = true;
        options.Lockout.MaxFailedAccessAttempts = 5;
        options.Lockout.DefaultLockoutTimeSpan = TimeSpan.FromMinutes(15);
    })
    .AddEntityFrameworkStores<AppDbContext>()
    .AddDefaultTokenProviders();

    // ─── JWT Authentication ────────────────────
    var jwtKey = builder.Configuration["Jwt:Secret"]
        ?? throw new InvalidOperationException("JWT Secret not configured.");

    builder.Services.AddAuthentication(options =>
    {
        options.DefaultAuthenticateScheme = JwtBearerDefaults.AuthenticationScheme;
        options.DefaultChallengeScheme = JwtBearerDefaults.AuthenticationScheme;
    })
    .AddJwtBearer(options =>
    {
        options.Events = new JwtBearerEvents { OnTokenValidated = async context => {
            var userManager = context.HttpContext.RequestServices.GetRequiredService<UserManager<ApplicationUser>>();
            var id = context.Principal?.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value;
            var user = id == null ? null : await userManager.FindByIdAsync(id);
            if (user?.IsActive != true || context.Principal?.FindFirst("sst")?.Value != user.SecurityStamp)
                context.Fail("Session invalidated. Sign in again.");
        }};
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidateAudience = true,
            ValidateLifetime = true,
            ValidateIssuerSigningKey = true,
            ValidIssuer = builder.Configuration["Jwt:Issuer"],
            ValidAudience = builder.Configuration["Jwt:Audience"],
            IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(jwtKey)),
            ClockSkew = TimeSpan.Zero
        };
    });

    builder.Services.AddAuthorization();
    builder.Services.AddRateLimiter(options => {
        options.RejectionStatusCode = StatusCodes.Status429TooManyRequests;
        options.AddPolicy("auth", context => RateLimitPartition.GetFixedWindowLimiter(
            context.Connection.RemoteIpAddress?.ToString() ?? "unknown",
            _ => new FixedWindowRateLimiterOptions { PermitLimit = 30,
                Window = TimeSpan.FromMinutes(10), QueueLimit = 0 }));
        options.AddPolicy("capture", context => RateLimitPartition.GetFixedWindowLimiter(
            context.User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value ?? "unauthenticated",
            _ => new FixedWindowRateLimiterOptions { PermitLimit = 120,
                Window = TimeSpan.FromMinutes(1), QueueLimit = 0 }));
        options.AddPolicy("account-export", context => RateLimitPartition.GetFixedWindowLimiter(
            context.User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value ?? "unauthenticated",
            _ => new FixedWindowRateLimiterOptions { PermitLimit = 120,
                Window = TimeSpan.FromMinutes(1), QueueLimit = 0 }));
    });
    builder.Services.AddSingleton(TimeProvider.System);
    var keyDirectory = builder.Configuration["Authentication:DataProtection:KeyDirectory"]
        ?? Path.Combine(builder.Environment.ContentRootPath, ".auth", "keys");
    Directory.CreateDirectory(keyDirectory);
    var protection = builder.Services.AddDataProtection().SetApplicationName("MediScan.Auth")
        .PersistKeysToFileSystem(new DirectoryInfo(keyDirectory));
    var protectionCertificate = builder.Configuration["Authentication:DataProtection:CertificatePath"];
    if (!string.IsNullOrWhiteSpace(protectionCertificate))
        protection.ProtectKeysWithCertificate(X509CertificateLoader.LoadPkcs12FromFile(protectionCertificate,
            builder.Configuration["Authentication:DataProtection:CertificatePassword"]));
    else if (OperatingSystem.IsWindows()) protection.ProtectKeysWithDpapi();
    else if (!builder.Environment.IsDevelopment())
        throw new InvalidOperationException("Configure a Data Protection certificate before running outside development on this platform.");
    builder.Services.AddSingleton<IEmailOtpStore>(sp => DatabaseOptions.IsSqlite(connStr, builder.Configuration["Database:Provider"])
        ? new PersistentEmailOtpStore(builder.Configuration["Authentication:Otp:DatabasePath"] ?? Path.Combine(builder.Environment.ContentRootPath, ".auth", "verification.db"),
            sp.GetRequiredService<TimeProvider>(), sp.GetRequiredService<IDataProtectionProvider>())
        : new PostgresEmailOtpStore(connStr, sp.GetRequiredService<TimeProvider>(), sp.GetRequiredService<IDataProtectionProvider>()));
    builder.Services.AddScoped<IVerificationEmailSender, SmtpEmailSender>();
    builder.Services.AddSingleton<IGoogleIdentityVerifier, GoogleIdentityVerifier>();
    builder.Services.AddScoped<AccountAccessService>();
    builder.Services.AddScoped<AccountDeletionService>();
    builder.Services.AddSingleton<IDeletionLedger>(sp => new DeletionLedger(
        builder.Configuration["Privacy:DeletionLedgerPath"] ?? Path.Combine(builder.Environment.ContentRootPath, ".privacy", "deletions.db"),
        sp.GetRequiredService<IDataProtectionProvider>()));
    builder.Services.AddScoped<AccountDeletionProcessor>();
    builder.Services.AddHostedService<AccountDeletionWorker>();
    builder.Services.AddScoped<DeletedRecordPurger>();
    if (builder.Configuration.GetValue<bool>("DataRetention:DeletedRecordPurgeEnabled"))
        builder.Services.AddHostedService<DeletedRecordPurgeWorker>();
    builder.Services.AddHttpClient("capture-guide", client => client.Timeout = TimeSpan.FromSeconds(10));
    builder.Services.AddHttpClient("image-storage", client => client.Timeout = TimeSpan.FromSeconds(30));
    builder.Services.AddHttpClient("readiness", client => client.Timeout = TimeSpan.FromSeconds(3));

    // ─── CORS ──────────────────────────────────
    builder.Services.AddCors(options =>
    {
        options.AddPolicy("MediScanPolicy", policy =>
        {
            var origins = builder.Configuration.GetSection("AllowedOrigins").Get<string[]>()
                          ?? new[] { "http://localhost:19006", "http://localhost:3000" };
            if (builder.Environment.IsDevelopment())
                policy.SetIsOriginAllowed(origin => Uri.TryCreate(origin, UriKind.Absolute, out var uri)
                    && uri.Scheme == "http" && uri.Port == 8081);
            else policy.WithOrigins(origins);
            policy
                  .AllowAnyHeader()
                  .AllowAnyMethod()
                  .AllowCredentials();
        });
    });

    // ─── Application Services ──────────────────
    builder.Services.AddHttpClient<IDocumentOcrService, DocumentOcrService>(client => client.Timeout = TimeSpan.FromSeconds(90));
    builder.Services.AddScoped<IAuthService, AuthService>();
    builder.Services.AddScoped<IAuditService, AuditService>();
    builder.Services.AddScoped<IDoctorService, DoctorService>();
    builder.Services.AddScoped<IStorageService>(sp =>
    {
        var config = sp.GetRequiredService<IConfiguration>();
        var connStr = config["Azure:StorageConnectionString"] ?? "";

        // Auto-select: Azure Blob if configured, local disk otherwise
        IStorageService rawStorage = !string.IsNullOrWhiteSpace(connStr)
            ? new AzureBlobStorageService(config)
            : new LocalStorageService(
                config,
                sp.GetRequiredService<Microsoft.AspNetCore.Hosting.IWebHostEnvironment>(),
                sp.GetRequiredService<Microsoft.Extensions.Logging.ILogger<LocalStorageService>>()
            );
        return new AccountStorageService(new SanitizedImageStorageService(rawStorage,
            sp.GetRequiredService<IHttpClientFactory>().CreateClient("image-storage"), config), sp.GetRequiredService<AppDbContext>());
    });
    builder.Services.AddScoped<IScanService, ScanService>();
    builder.Services.AddScoped<IMedicationService, MedicationService>();

    // Register AppDbContext as IAppDbContext for ScanService + MedicationService
    builder.Services.AddScoped<IAppDbContext>(sp =>
        (IAppDbContext)sp.GetRequiredService<AppDbContext>());

    // AI Inference Service (typed HttpClient)
    builder.Services.AddHttpClient<IAiInferenceService, AiInferenceService>(client =>
    {
        client.Timeout = TimeSpan.FromSeconds(60);
    });

    // Drug data service (OpenFDA + Pakistan DAP) — typed HttpClient
    builder.Services.AddHttpClient<IDrugDataService, DrugDataService>(client =>
    {
        client.Timeout = TimeSpan.FromSeconds(15);
        client.DefaultRequestHeaders.Add("User-Agent", "MediScanAI/1.0 (contact@mediscan.ai)");
    });

    // GPT-4o Recommendation service — typed HttpClient
    builder.Services.AddHttpClient<IRecommendationService, RecommendationService>(client =>
    {
        client.Timeout = TimeSpan.FromSeconds(30);
    });

    // ─── Controllers ───────────────────────────
    builder.Services.AddControllers()
        .AddJsonOptions(options =>
        {
            options.JsonSerializerOptions.PropertyNamingPolicy =
                System.Text.Json.JsonNamingPolicy.CamelCase;
            options.JsonSerializerOptions.Converters.Add(
                new System.Text.Json.Serialization.JsonStringEnumConverter());
        });

    // ─── Swagger ───────────────────────────────
    builder.Services.AddEndpointsApiExplorer();
    builder.Services.AddSwaggerGen(c =>
    {
        c.SwaggerDoc("v1", new OpenApiInfo
        {
            Title = "MediScan AI API",
            Version = "v1",
            Description = "HIPAA-aware Medical AI Detection API",
            Contact = new OpenApiContact { Name = "Faizan", Email = "dev@mediscan.ai" }
        });

        // JWT in Swagger
        c.AddSecurityDefinition("Bearer", new OpenApiSecurityScheme
        {
            Description = "JWT Authorization. Enter: Bearer {token}",
            Name = "Authorization",
            In = ParameterLocation.Header,
            Type = SecuritySchemeType.ApiKey,
            Scheme = "Bearer"
        });

        c.AddSecurityRequirement(new OpenApiSecurityRequirement
        {
            {
                new OpenApiSecurityScheme
                {
                    Reference = new OpenApiReference
                    {
                        Type = ReferenceType.SecurityScheme,
                        Id = "Bearer"
                    }
                },
                Array.Empty<string>()
            }
        });
    });

    // ─────────────────────────────────────────────
    var app = builder.Build();
    // ─────────────────────────────────────────────

    if (initializeDatabase)
    {
        using var scope = app.Services.CreateScope();
        var database = scope.ServiceProvider.GetRequiredService<AppDbContext>();
        await database.Database.MigrateAsync();
        var roles = scope.ServiceProvider.GetRequiredService<RoleManager<IdentityRole>>();
        foreach (var role in new[] { "User", "Doctor", "Admin" })
            if (!await roles.RoleExistsAsync(role))
            {
                var result = await roles.CreateAsync(new IdentityRole(role));
                if (!result.Succeeded) throw new InvalidOperationException("Role provisioning failed.");
            }
        _ = scope.ServiceProvider.GetRequiredService<IDeletionLedger>().Snapshot();
        Log.Information("Database initialized. No demo accounts were created.");
        return;
    }

    // Run migrations + seed on startup (dev only)
    if (app.Environment.IsDevelopment())
    {
        using var scope = app.Services.CreateScope();
        var db          = scope.ServiceProvider.GetRequiredService<AppDbContext>();
        var userManager = scope.ServiceProvider.GetRequiredService<UserManager<ApplicationUser>>();
        var roleManager = scope.ServiceProvider.GetRequiredService<RoleManager<IdentityRole>>();
        var seedLogger  = scope.ServiceProvider.GetRequiredService<ILogger<Program>>();

        await DatabaseSeeder.SeedAsync(db, userManager, roleManager, seedLogger);
    }

    using (var privacyScope = app.Services.CreateScope())
        await privacyScope.ServiceProvider.GetRequiredService<AccountDeletionProcessor>().RecoverLedgerIntentsAsync(CancellationToken.None);

    app.UseMiddleware<ExceptionMiddleware>();
    app.UseSerilogRequestLogging();

    // Serve local uploaded files in development
    // Medical uploads are served only by the authenticated, owner-scoped MediaController.

    if (app.Environment.IsDevelopment())
    {
        app.UseSwagger();
        app.UseSwaggerUI(c => c.SwaggerEndpoint("/swagger/v1/swagger.json", "MediScan AI v1"));
    }

    if (!app.Environment.IsDevelopment()) app.UseHttpsRedirection();
    app.UseCors("MediScanPolicy");
    app.UseAuthentication();
    app.UseAuthorization();
    app.UseRateLimiter();
    app.MapControllers();

    Log.Information("🚀 MediScan AI API starting on {Environment}", app.Environment.EnvironmentName);
    await app.RunAsync();
}
catch (HostAbortedException) { /* EF design-time host discovery. */ }
catch (Exception ex)
{
    Log.Fatal(ex, "Application startup failed");
    Environment.ExitCode = 1;
}
finally
{
    Log.CloseAndFlush();
}
