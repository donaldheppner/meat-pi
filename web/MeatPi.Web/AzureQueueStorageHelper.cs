using System;
using System.Text.Json;
using System.Threading.Tasks;
using Azure.Storage.Queues;

namespace MeatPi.Web
{
    public class AzureQueueStorageHelper
    {
        private static string connectionString;
        private static string ConnectionString
        {
            get
            {
                if (connectionString == null) throw new InvalidOperationException($"{nameof(AzureQueueStorageHelper)} has not been initialized.");
                return connectionString;
            }
            set { connectionString = value; }
        }

        public static void Init(string storageConnectionString)
        {
            ConnectionString = storageConnectionString;
        }

        private static QueueClient GetQueue(string name)
        {
            return new QueueClient(ConnectionString, name);
        }

        public static async Task QueueMessage(string queueName, string message)
        {
            if (string.IsNullOrEmpty(queueName)) throw new ArgumentNullException(nameof(queueName));
            if (string.IsNullOrEmpty(message)) throw new ArgumentNullException(nameof(message));

            var queue = GetQueue(queueName);
            await queue.SendMessageAsync(message);
        }

        /// <summary>
        /// Converts message to JSON and serializes as a string
        /// </summary>
        public static async Task QueueMessage(string queueName, object message)
        {
            if (message == null) throw new ArgumentNullException(nameof(message));

            var queue = GetQueue(queueName);
            await queue.SendMessageAsync(JsonSerializer.Serialize(message));
        }
    }
}
