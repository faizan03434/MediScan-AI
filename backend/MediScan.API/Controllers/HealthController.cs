using Microsoft.AspNetCore.Mvc;

namespace MediScan.API.Controllers;

[ApiController]
[Route("api/v1/[controller]")]
public class HealthController : ControllerBase
{
    /// <summary>API health check</summary>
    [HttpGet]
    public IActionResult Check() =>
        Ok(new { Status = "Healthy", Timestamp = DateTime.UtcNow, Version = "1.0.0" });
}
