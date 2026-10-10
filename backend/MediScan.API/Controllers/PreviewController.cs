using System.Net;
using Microsoft.AspNetCore.Mvc;

namespace MediScan.API.Controllers;

// Development-only handoff for Android, iPhone and browser previews.
[ApiController]
public sealed class PreviewController(IWebHostEnvironment environment) : ControllerBase
{
    [HttpGet("/preview")]
    public IActionResult Index()
    {
        if (!environment.IsDevelopment()) return NotFound();
        var host = WebUtility.HtmlEncode(Request.Host.Host);
        var html = $$"""
        <!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Open MediScan</title>
        <style>body{background:#f6f7f9;color:#182230;font:16px system-ui;margin:0;padding:32px 20px}main{max-width:440px;margin:30px auto;background:white;border:1px solid #e4e7ec;border-radius:24px;padding:28px}h1{font-size:28px}p,li{line-height:1.6;color:#475467}a{color:#176b5b}.button{display:block;background:#176b5b;color:white;text-align:center;padding:16px;text-decoration:none;border-radius:12px;margin:20px 0}.secondary{background:#eef4f1;color:#176b5b}small{color:#667085}</style></head>
        <body><main><small>MEDISCAN AI · MOBILE PREVIEW</small><h1>Your health journal</h1><ol><li>Install Expo Go: <a href="https://apps.apple.com/app/expo-go/id982107779">iPhone App Store</a> or <a href="https://play.google.com/store/apps/details?id=host.exp.exponent">Android Play Store</a>.</li><li>Keep your phone and this computer on the same Wi-Fi.</li><li>Tap the button below and allow Expo Go to open. On Android you can also scan the Expo terminal QR from inside Expo Go.</li></ol>
        <a class="button" href="exp://{{host}}:8081">Open in Expo Go</a><a class="button secondary" href="http://{{host}}:8081">Open browser preview</a>
        <p>If Expo Go does not open, enter <strong>exp://{{host}}:8081</strong> inside Expo Go. Keep the development servers running.</p><p><a href="/api/v1/health">Check API connection</a></p><small>Use test data only. Clinical models are not validated. Native Google sign-in needs a development build.</small></main></body></html>
        """;
        Response.Headers.CacheControl = "no-store";
        return Content(html, "text/html; charset=utf-8");
    }
}
