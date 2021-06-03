using System;
using System.Text.Json;
using System.Collections.Generic;
using System.Threading.Tasks;
using Microsoft.WindowsAzure.Storage;
using Microsoft.WindowsAzure.Storage.Queue;

namespace MeatPi.Functions
{
    public class AzureQueueStorageHelper
    {
        const string StorageConfiguration = "AzureWebJobsStorage";
        private static readonly CloudStorageAccount StorageAccount = CloudStorageAccount.Parse(Environment.GetEnvironmentVariable(StorageConfiguration));
        private static readonly SortedSet<string> CreatedQueues = new SortedSet<string>();
        private static CloudQueueClient Client => StorageAccount.CreateCloudQueueClient();

        private static async Task<CloudQueue> GetQueue(string name)
        {
            var queue = Client.GetQueueReference(name);

            if (!CreatedQueues.Contains(name))
            {
                await queue.CreateIfNotExistsAsync();
                CreatedQueues.Add(name);
            }

            return queue;
        }

        public static async Task QueueMessage(string queueName, string message)
        {
            if (string.IsNullOrEmpty(queueName)) throw new ArgumentNullException(nameof(queueName));
            if (string.IsNullOrEmpty(message)) throw new ArgumentNullException(nameof(message));

            var queue = await GetQueue(queueName);
            await queue.AddMessageAsync(new CloudQueueMessage(message));
        }

        /// <summary>
        /// Converts message to JSON and serializes as a string
        /// </summary>
        public static async Task QueueMessage(string queueName, object message)
        {
            if (message == null) throw new ArgumentNullException(nameof(message));

            var queue = await GetQueue(queueName);
            await queue.AddMessageAsync(new CloudQueueMessage(JsonSerializer.Serialize(message)));
        }
    }
}
