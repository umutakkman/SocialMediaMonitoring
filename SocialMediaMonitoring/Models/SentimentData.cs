using System.Text.Json.Serialization;

namespace SocialMediaMonitoring.Models
{
    public class SentimentData
    {
        public int Positive { get; set; }
        public int Neutral { get; set; }
        public int Negative { get; set; }
    }
}
