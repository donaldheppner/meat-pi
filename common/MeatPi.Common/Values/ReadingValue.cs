using System.Text.Json.Serialization;

namespace MeatPi.Common.Values
{
    public class ReadingValue
    {
        [JsonPropertyName("pin")]
        public int Pin { get; set; }

        [JsonPropertyName("value")]
        public int Value { get; set; }

        [JsonPropertyName("resistance")]
        public double Resistance { get; set; }

        [JsonPropertyName("kelvins")]
        public double Kelvins { get; set; }
    }
}
