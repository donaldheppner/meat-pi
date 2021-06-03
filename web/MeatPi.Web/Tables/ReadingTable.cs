using Microsoft.Azure.Cosmos.Table;
using System;

namespace MeatPi.Web.Tables
{
    public class ReadingTable : TableEntity
    {
        public const string TableName = "Reading";

        public ReadingTable() { }
        public ReadingTable(string deviceId, string cookId, string time) : base(CreatePartitionKey(deviceId, cookId), time) { }

        [IgnoreProperty]
        public string DeviceId => PartitionKey.Split("|")[0];

        [IgnoreProperty]
        public string CookId => PartitionKey.Split("|")[1];

        [IgnoreProperty]
        public string Time => RowKey;

        public double ChamberTarget { get; set; }
        public bool IsCookerOn { get; set; }
        public string Readings { get; set; }

        public static string CreatePartitionKey(string deviceId, string cookId) => string.Join("|", deviceId, cookId);

    }
}
