namespace SocialMediaMonitoring.Models
{
    public class MastodonRequest
    {
        public string Text { get; set; }
        public int MaxResults { get; set; } = 100;
    }
}
