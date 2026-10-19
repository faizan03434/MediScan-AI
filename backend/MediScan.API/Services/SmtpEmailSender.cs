using System.Net;
using System.Net.Mail;

namespace MediScan.API.Services;

public interface IVerificationEmailSender
{
    bool IsConfigured { get; }
    Task SendCodeAsync(string email, string code, string purpose);
}

public sealed class SmtpEmailSender(IConfiguration config) : IVerificationEmailSender
{
    public bool IsConfigured => !string.IsNullOrWhiteSpace(config["Email:Smtp:Password"])
        && !string.IsNullOrWhiteSpace(config["Email:Smtp:Username"]);
    public async Task SendCodeAsync(string email, string code, string purpose)
    {
        if (!IsConfigured) throw new InvalidOperationException("Email delivery is not configured. Add the SMTP app password on the server.");
        var sender = config["Email:From"] ?? "iamfaizan884@gmail.com";
        using var message = new MailMessage(new MailAddress(sender, "MediScan"), new MailAddress(email))
        {
            Subject = purpose == "registration" ? "Verify your MediScan email" : "Reset your MediScan password",
            Body = $"Your MediScan verification code is {code}.\n\nIt expires in 10 minutes and can be used once. Do not share this code. If you did not request it, ignore this email."
        };
        using var smtp = new SmtpClient(config["Email:Smtp:Host"] ?? "smtp.gmail.com",
            config.GetValue("Email:Smtp:Port", 587))
        {
            EnableSsl = true,
            Credentials = new NetworkCredential(config["Email:Smtp:Username"], config["Email:Smtp:Password"]),
            Timeout = 15000
        };
        using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(15));
        await smtp.SendMailAsync(message, deadline.Token);
    }
}
