using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using SocialMediaMonitoring.Models;

namespace SocialMediaMonitoring.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    public class AnalysisController : ControllerBase
    {
        private readonly HttpClient _httpClient;
        private readonly string _pythonApiUrl;

        public AnalysisController(IHttpClientFactory httpClientFactory, IConfiguration configuration)
        {
            // Creating a client with extended timeout for long-running operations
            _httpClient = httpClientFactory.CreateClient();

            // Setting a timeout (5 minutes) for analyzing datasets
            _httpClient.Timeout = TimeSpan.FromMinutes(5);

            // Getting API URL from configuration or environment variable, with fallback
            _pythonApiUrl = Environment.GetEnvironmentVariable("PYTHONAPI_URL")
                            ?? configuration["PythonApi:Url"]
                            ?? "http://localhost:5002"; // Use this for localhost. For docker (used in live demos) used "http://pythonapi:5002"

            _pythonApiUrl = _pythonApiUrl.TrimEnd('/') + "/analyze";
        }

        [HttpPost("analyze-mastodon")]
        public async Task<IActionResult> AnalyzeMastodon([FromBody] MastodonRequest request)
        {
            if (string.IsNullOrWhiteSpace(request.Text))
            {
                return BadRequest(new { error = "No keyword provided." });
            }

            // Validate maxResults
            int maxResults = request.MaxResults;
            if (maxResults <= 0)
            {
                maxResults = 100; // Default value
            }

            // Serialize our request to JSON payload including maxResults
            var payload = new { text = request.Text, maxResults = maxResults };
            var json = JsonSerializer.Serialize(payload);

            var content = new StringContent(json, Encoding.UTF8, "application/json");

            HttpResponseMessage response;
            try
            {
                // Use a cancellation token with a timeout to prevent indefinite waiting
                using var cts = new CancellationTokenSource(TimeSpan.FromMinutes(5));
                response = await _httpClient.PostAsync(_pythonApiUrl, content, cts.Token);
            }
            catch (TaskCanceledException)
            {
                return StatusCode(504, new
                {
                    error = "Analysis service took too long to respond. This usually happens with large datasets or complex analysis.",
                    details = "The operation timed out. You might try again with a different or more specific keyword that returns fewer posts."
                });
            }
            catch (OperationCanceledException)
            {
                return StatusCode(504, new
                {
                    error = "Analysis operation was canceled"
                });
            }
            catch (HttpRequestException ex)
            {
                return StatusCode(503, new
                {
                    error = "Unable to reach analysis service",
                    details = ex.Message
                });
            }

            var responseBody = await response.Content.ReadAsStringAsync();

            if (!response.IsSuccessStatusCode)
            {
                return StatusCode((int)response.StatusCode, responseBody);
            }

            // Parse the response to extract summary and sentiment data
            try
            {
                var options = new JsonSerializerOptions
                {
                    PropertyNameCaseInsensitive = true
                };

                var result = JsonSerializer.Deserialize<MastodonAnalysisResult>(responseBody, options);

                if (result == null)
                {
                    return StatusCode(500, new { error = "API returned empty or invalid result" });
                }

                return Ok(result);
            }
            catch (JsonException ex)
            {
                return StatusCode(500, new
                {
                    error = "Error processing API response",
                    details = ex.Message
                });
            }
        }
    }
}
