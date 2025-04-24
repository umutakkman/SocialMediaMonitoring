namespace SocialMediaMonitoring.Models
{
    public class TimeSentimentData
    {
        public string Period { get; set; } = string.Empty;
        public int Count { get; set; }
        public SentimentData Sentiment { get; set; } = new SentimentData();
    }
}
