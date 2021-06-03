using Microsoft.Azure.Cosmos.Table;
using MeatPi.Common.Values;

namespace MeatPi.Common.Tables
{
    public class CookTable : TableEntity
    {
        public const string TableName = "Cook";

        public CookTable() { }
        public CookTable(string deviceId, string cookId) : base(deviceId, cookId) { }

        [IgnoreProperty]
        public string DeviceId => PartitionKey;

        [IgnoreProperty]
        public string CookId => RowKey;

        public string StartTime { get; set; }
        public string LastTime { get; set; }

        public static CookTable FromReading(CookReadingValue reading)
        {
            return new CookTable(reading.DeviceId, reading.CookId)
            {
                StartTime = reading.CookStartTime,
                LastTime = reading.Time
            };
        }
    }
}
