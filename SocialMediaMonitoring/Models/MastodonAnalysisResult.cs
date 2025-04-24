using System.Text.Json.Serialization;

namespace SocialMediaMonitoring.Models
{
    public class MastodonAnalysisResult
    {
        public string Summary { get; set; } = string.Empty;
        public SentimentData Sentiment { get; set; } = new SentimentData();
        public List<TimeSentimentData> SentimentOverTime { get; set; } = new List<TimeSentimentData>();
        public List<string> RelatedKeywords { get; set; } = new List<string>();
    }
}
