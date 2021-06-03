using System;
using System.Text.Json;
using System.Threading.Tasks;
using Microsoft.Azure.WebJobs;
using Microsoft.Extensions.Logging;
using MeatPi.Common;
using MeatPi.Common.Tables;
using MeatPi.Common.Values;

namespace MeatPi.Functions
{
    public static class TemperatureReadingFunctions
    {
        /// <summary>
        /// Is triggered when an event comes in via service bus; stores the data in a table and writes it to a queue for the web app to process
        /// </summary>
        [FunctionName("QueueReading")]
        public static async Task Run([ServiceBusTrigger("readings", Connection = "meatpi_SERVICEBUS")] string readingsQueueItem, ILogger log)
        {
            AzureTableHelper.Init(Environment.GetEnvironmentVariable("AzureWebJobsStorage"));
            AzureQueueStorageHelper.Init(Environment.GetEnvironmentVariable("AzureWebJobsStorage"));
            const string ReadingsQueue = "readings";

            log.LogInformation($"C# ServiceBus queue trigger function processed message: {readingsQueueItem}");

            var reading = JsonSerializer.Deserialize<CookReadingValue>(readingsQueueItem);

            await AzureTableHelper.InsertOrReplace<CookTable>(CookTable.TableName, CookTable.FromReading(reading));
            await AzureTableHelper.InsertOrReplace<ReadingTable>(ReadingTable.TableName, ReadingTable.FromReading(reading));
            await AzureQueueStorageHelper.QueueMessage(ReadingsQueue, reading);
        }
    }
}
