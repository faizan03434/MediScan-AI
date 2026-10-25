using MediScan.API.Middleware;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Logging;

namespace MediScan.Tests;

public class ExceptionPrivacyTests
{
    private sealed class Logger : ILogger<ExceptionMiddleware>
    {
        public readonly List<string> Messages = [];
        public bool ExceptionObjectLogged;
        public IDisposable? BeginScope<TState>(TState state) where TState : notnull => null;
        public bool IsEnabled(LogLevel level) => true;
        public void Log<TState>(LogLevel level, EventId id, TState state, Exception? exception, Func<TState, Exception?, string> formatter)
        { Messages.Add(formatter(state, exception)); ExceptionObjectLogged |= exception != null; }
    }
    [Fact]
    public async Task UnexpectedFailuresJournalOnlyTypeAndTraceWithoutPrivateProviderText()
    {
        var logger = new Logger();
        var middleware = new ExceptionMiddleware(_ => throw new InvalidOperationException("private-patient and secret-token"), logger);
        var context = new DefaultHttpContext(); context.Response.Body = new MemoryStream();
        await middleware.InvokeAsync(context);
        Assert.Equal(500, context.Response.StatusCode); Assert.False(logger.ExceptionObjectLogged);
        Assert.Single(logger.Messages); Assert.DoesNotContain("private-patient", logger.Messages[0]);
        Assert.DoesNotContain("secret-token", logger.Messages[0]);
        context.Response.Body.Position = 0;
        Assert.DoesNotContain("secret-token", await new StreamReader(context.Response.Body).ReadToEndAsync());
    }
    [Fact]
    public async Task ClientCancellationDoesNotCreateAFakeServerFailure()
    {
        var logger = new Logger(); using var cancellation = new CancellationTokenSource(); cancellation.Cancel();
        var context = new DefaultHttpContext { RequestAborted = cancellation.Token }; context.Response.Body = new MemoryStream();
        await new ExceptionMiddleware(_ => throw new OperationCanceledException(), logger).InvokeAsync(context);
        Assert.Empty(logger.Messages); Assert.Equal(0, context.Response.Body.Length);
    }
}
