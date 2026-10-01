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

// ─────────────────────────────────────────────
// Bootstrap Serilog early
// ─────────────────────────────────────────────
Log.Logger = new LoggerConfiguration()
    .WriteTo.Console()
    .CreateBootstrapLogger();

try
{
    var builder = WebApplication.CreateBuilder(args);

    // ─── Serilog ───────────────────────────────
    builder.Host.UseSerilog((ctx, lc) => lc
        .ReadFrom.Configuration(ctx.Configuration)
        .WriteTo.Console());

    // ─── Database ──────────────────────────────
    // Auto-select: SQLite for dev (no PostgreSQL password needed), PostgreSQL for prod
    var connStr = builder.Configuration.GetConnectionString("DefaultConnection") ?? "";
    var useSqlite = connStr.StartsWith("Data Source=") || connStr.Contains(".db") ||
                    builder.Configuration["Database:Provider"] == "sqlite";

    builder.Services.AddDbContext<AppDbContext>(options =>
    {
        if (useSqlite)
        {
            var sqlitePath = connStr.Replace("Data Source=", "").Replace(";", "").Trim();
            if (string.IsNullOrEmpty(sqlitePath) || !connStr.Contains("="))
                sqlitePath = Path.Combine(builder.Environment.ContentRootPath, "mediscan_dev.db");
            options.UseSqlite($"Data Source={sqlitePath}");
            Log.Information("Database: SQLite at {Path}", sqlitePath);
        }
        else
        {
            options.UseNpgsql(connStr);
            Log.Information("Database: PostgreSQL");
        }
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

    // ─── CORS ──────────────────────────────────
    builder.Services.AddCors(options =>
    {
        options.AddPolicy("MediScanPolicy", policy =>
        {
            var origins = builder.Configuration.GetSection("AllowedOrigins").Get<string[]>()
                          ?? new[] { "http://localhost:19006", "http://localhost:3000" };
            policy.WithOrigins(origins)
                  .AllowAnyHeader()
                  .AllowAnyMethod()
                  .AllowCredentials();
        });
    });

    // ─── Application Services ──────────────────
    builder.Services.AddScoped<IAuthService, AuthService>();
    builder.Services.AddScoped<IAuditService, AuditService>();
    builder.Services.AddScoped<IDoctorService, DoctorService>();
    builder.Services.AddScoped<IStorageService>(sp =>
    {
        var config = sp.GetRequiredService<IConfiguration>();
        var connStr = config["Azure:StorageConnectionString"] ?? "";

        // Auto-select: Azure Blob if configured, local disk otherwise
        if (!string.IsNullOrWhiteSpace(connStr))
            return new AzureBlobStorageService(config);
        else
            return new LocalStorageService(
                config,
                sp.GetRequiredService<Microsoft.AspNetCore.Hosting.IWebHostEnvironment>(),
                sp.GetRequiredService<Microsoft.Extensions.Logging.ILogger<LocalStorageService>>()
            );
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

    app.UseMiddleware<ExceptionMiddleware>();
    app.UseSerilogRequestLogging();

    // Serve local uploaded files in development
    app.UseStaticFiles();

    if (app.Environment.IsDevelopment())
    {
        app.UseSwagger();
        app.UseSwaggerUI(c => c.SwaggerEndpoint("/swagger/v1/swagger.json", "MediScan AI v1"));
    }

    app.UseHttpsRedirection();
    app.UseCors("MediScanPolicy");
    app.UseAuthentication();
    app.UseAuthorization();
    app.MapControllers();

    Log.Information("🚀 MediScan AI API starting on {Environment}", app.Environment.EnvironmentName);
    await app.RunAsync();
}
catch (Exception ex)
{
    Log.Fatal(ex, "Application startup failed");
}
finally
{
    Log.CloseAndFlush();
}
