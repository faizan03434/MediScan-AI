using System.ComponentModel.DataAnnotations;
using System.Security.Claims;
using MediScan.API.Services;
using MediScan.Core.DTOs.Common;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.RateLimiting;

namespace MediScan.API.Controllers;

public sealed class DeletionStatusRequest { [Required, StringLength(43, MinimumLength = 43)] public string Receipt { get; set; } = ""; }

[ApiController, Authorize, Route("api/v1/account/deletion"), EnableRateLimiting("auth")]
[ResponseCache(NoStore = true, Location = ResponseCacheLocation.None)]
public sealed class AccountDeletionController(AccountDeletionService deletion) : ControllerBase
{
    [HttpPost("code")]
    public async Task<IActionResult> Code()
    {
        var id = User.FindFirstValue(ClaimTypes.NameIdentifier);
        if (string.IsNullOrEmpty(id)) return Unauthorized();
        return Ok(ApiResponse<OtpChallenge>.Ok(await deletion.SendCodeAsync(id)));
    }
    [HttpPost]
    public async Task<IActionResult> QueueDeletion(DeleteAccountRequest request)
    {
        var id = User.FindFirstValue(ClaimTypes.NameIdentifier);
        if (string.IsNullOrEmpty(id)) return Unauthorized();
        return Accepted(ApiResponse<DeletionReceipt>.Ok(await deletion.RequestAsync(id, request), "Deletion queued; account access disabled."));
    }
    // Capability is in the request body to avoid putting the secret receipt in URL logs/history.
    [AllowAnonymous, HttpPost("status")]
    public async Task<IActionResult> Status(DeletionStatusRequest request)
    {
        Response.Headers.CacheControl = "private, no-store";
        var status = await deletion.StatusAsync(request.Receipt);
        return status == null ? NotFound() : Ok(ApiResponse<DeletionStatus>.Ok(status));
    }
}
