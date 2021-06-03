using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace MeatPi.Common.Values
{
    public class CookReadingValue
    {
        [JsonPropertyName("device_id")]
        public string DeviceId { get; set; }

        [JsonPropertyName("cook_id")]
        public string CookId { get; set; }

        [JsonPropertyName("time")]
        public string Time { get; set; }

        [JsonPropertyName("cook_start_time")]
        public string CookStartTime { get; set; }

        [JsonPropertyName("chamber_target")]
        public double ChamberTarget { get; set; }

        [JsonPropertyName("cooker_on")]
        public bool IsCookerOn { get; set; }

        [JsonPropertyName("readings")]
        public List<ReadingValue> Readings { get; set; }
    }

}
