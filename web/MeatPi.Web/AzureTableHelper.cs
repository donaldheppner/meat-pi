using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using Dasync.Collections;
using Microsoft.Azure.Cosmos.Table;

namespace MeatPi.Web
{
    public static class AzureTableHelper
    {
        private static CloudStorageAccount storageAccount;
        private static CloudStorageAccount StorageAccount
        {
            get
            {
                if (storageAccount == null) throw new InvalidOperationException($"{nameof(AzureTableHelper)} has not been initialized.");
                return storageAccount;
            }
            set { storageAccount = value; }
        }

        public static void Init(string storageConnectionString)
        {
            StorageAccount = CloudStorageAccount.Parse(storageConnectionString);
        }

        public const string PartitionKey = nameof(TableEntity.PartitionKey);
        public const string RowKey = nameof(TableEntity.RowKey);
        public const string Timestamp = nameof(TableEntity.Timestamp);

        public static readonly string[] BuiltInOperators = {
            QueryComparisons.Equal,
            QueryComparisons.GreaterThan,
            QueryComparisons.GreaterThanOrEqual,
            QueryComparisons.LessThan,
            QueryComparisons.LessThanOrEqual,
            QueryComparisons.NotEqual,
        };

        public static class StringComparisons
        {
            public const string StartsWith = "startswith";
            public const string EndsWith = "endswith";
            public const string Contains = "contains";
        }

        public static readonly string[] StringOperators =
        {
            StringComparisons.StartsWith,
            StringComparisons.EndsWith,
            StringComparisons.Contains
        };

        public static readonly string[] Operators = BuiltInOperators.Concat(StringOperators).ToArray();

        private static readonly SortedSet<string> CreatedTables = new SortedSet<string>();

        public static string NewId => Guid.NewGuid().ToString("N");

        public static string EncodeString(string toEncode)
        {
            return Convert.ToBase64String(Encoding.UTF8.GetBytes(toEncode));
        }

        public static string DecodeString(string toDecode)
        {
            return Encoding.UTF8.GetString(Convert.FromBase64String(toDecode));
        }

        public static CloudTableClient Client => StorageAccount.CreateCloudTableClient();

        public static CloudTable GetTable(string tableName)
        {
            var result = Client.GetTableReference(tableName);

            // avoid calling CreateIfNotExists unnecessarily
            if (!CreatedTables.Contains(tableName))
            {
                result.CreateIfNotExists(null, new OperationContext());
                CreatedTables.Add(tableName);
            }

            return result;
        }

        public static async Task<List<T>> Query<T>(string tableName,
            params string[] conditions) where T : class, ITableEntity, new()
        {
            return await Query<T>(tableName, (IEnumerable<string>)conditions);
        }

        /// <summary>
        /// Aggregates all the results from a table (using the continuation token) before returning.
        /// </summary>
        public static async Task<List<T>> Query<T>(string tableName, IEnumerable<string> conditions, string conditionOperator = TableOperators.And) where T : class, ITableEntity, new()
        {
            if (conditions == null) throw new ArgumentNullException(nameof(conditions));
            var result = new List<T>();

            var table = GetTable(tableName);

            string aggregatedCondition = AggregateCondition(conditionOperator, conditions);
            if (aggregatedCondition == null) throw new ArgumentException("Query must have at least one condition", nameof(conditions));

            var query = new TableQuery<T>().Where(aggregatedCondition);
            TableContinuationToken token = null;

            do
            {
                var queryResult = await table.ExecuteQuerySegmentedAsync(query, token);
                token = queryResult.ContinuationToken;
                result.AddRange(queryResult.Results);
            } while (token != null);

            return result;
        }

        /// <summary>
        /// Streams back results and handles continuation tokens as needed
        /// </summary>
        public static IAsyncEnumerable<T> QueryStream<T>(string tableName,
            params string[] conditions) where T : class, ITableEntity, new()
        {
            return QueryStream<T>(tableName, (IEnumerable<string>)conditions);
        }

        /// <summary>
        /// Streams back results and handles continuation tokens as needed
        /// </summary>
        public static IAsyncEnumerable<T> QueryStream<T>(string tableName, IEnumerable<string> conditions,
            string conditionOperator = TableOperators.And) where T : class, ITableEntity, new()
        {
            if (conditions == null) throw new ArgumentNullException(nameof(conditions));

            return new AsyncEnumerable<T>(async yield =>
            {
                var table = GetTable(tableName);

                string aggregatedCondition = AggregateCondition(conditionOperator, conditions);
                if (aggregatedCondition == null)
                    throw new ArgumentException("Query must have at least one condition", nameof(conditions));

                var query = new TableQuery<T>().Where(aggregatedCondition);
                TableContinuationToken token = null;

                do
                {
                    var queryResult = await table.ExecuteQuerySegmentedAsync(query, token);
                    token = queryResult.ContinuationToken;
                    foreach (var item in queryResult.Results)
                        await yield.ReturnAsync(item);
                } while (token != null);
            });
        }

        // TODO: revise to avoid deep parenthetical nesting
        public static string AggregateCondition(string conditionOperator, params string[] conditions)
        {
            return AggregateCondition(conditionOperator, (IEnumerable<string>)conditions);
        }

        public static string AggregateCondition(string conditionOperator, IEnumerable<string> conditions)
        {
            string result = null;

            foreach (var condition in conditions)
            {
                result = result == null
                    ? condition
                    : TableQuery.CombineFilters(result, conditionOperator, condition);
            }

            return result;
        }

        public static async Task<T> Get<T>(string tableName, string partitionKey, string rowKey) where T : class, ITableEntity
        {
            var table = GetTable(tableName);
            var queryResult = await table.ExecuteAsync(TableOperation.Retrieve<T>(partitionKey, rowKey));
            return queryResult.Result as T;
        }

        private static void HandleETag<T>(T entity) where T : class, ITableEntity
        {
            if (entity.ETag == null) entity.ETag = "*";
        }

        private static void HandleETags<T>(IEnumerable<T> entity) where T : class, ITableEntity
        {
            foreach (var e in entity)
            {
                if (e.ETag == null) e.ETag = "*";
            }
        }

        public static async Task<TableResult> Insert<T>(string tableName, T entity) where T : class, ITableEntity
        {
            HandleETag(entity);

            var table = GetTable(tableName);
            return await table.ExecuteAsync(TableOperation.Insert(entity));
        }

        /// <summary>
        /// Inserts entities in batches of 100; all must have the same partition key
        /// </summary>
        /// <returns>All the table results (for each entity)</returns>
        public static async Task<List<TableResult>> Insert<T>(string tableName, List<T> entities) where T : class, ITableEntity
        {
            return await AbstractBatchOperation(tableName, entities, TableOperation.Insert);
        }

        /// <summary>
        /// Inserts or Merges entities in batches of 100; all must have the same partition key
        /// </summary>
        /// <returns>All the table results (for each entity)</returns>
        public static async Task<List<TableResult>> InsertOrMerge<T>(string tableName, List<T> entities) where T : class, ITableEntity
        {
            return await AbstractBatchOperation(tableName, entities, TableOperation.InsertOrMerge);
        }

        /// <summary>
        /// Inserts or Replaces entities in batches of 100; all must have the same partition key
        /// </summary>
        /// <returns>All the table results (for each entity)</returns>
        public static async Task<List<TableResult>> InsertOrReplace<T>(string tableName, List<T> entities) where T : class, ITableEntity
        {
            return await AbstractBatchOperation(tableName, entities, TableOperation.InsertOrReplace);
        }

        /// <summary>
        /// Deletes entities in batches of 100; all must have the same partition key
        /// </summary>
        /// <returns>All the table results (for each entity)</returns>
        public static async Task<List<TableResult>> Delete<T>(string tableName, List<T> entities) where T : class, ITableEntity
        {
            return await AbstractBatchOperation(tableName, entities, TableOperation.Delete);
        }

        /// <summary>
        /// Batches the specified operation
        /// </summary>
        /// <returns>All the table results (for each entity)</returns>
        public static async Task<List<TableResult>> AbstractBatchOperation<T>(string tableName, List<T> entities, Func<T, TableOperation> operation) where T : class, ITableEntity
        {
            HandleETags(entities);

            const int batchSize = 100;

            var results = new List<TableResult>();
            var table = GetTable(tableName);

            // ensure all entities have the same partition key
            if (entities.Count > 0)
            {
                string key = entities[0].PartitionKey;
                foreach (var entity in entities)
                {
                    if (entity.PartitionKey != key) throw new ArgumentException("Not all entities have the same partition key", nameof(entities));
                }
            }

            int index = 0;
            while (index < entities.Count)
            {
                var batch = new TableBatchOperation();
                foreach (var entity in entities.Skip(index).Take(batchSize))
                {
                    batch.Add(operation(entity));
                    index++;
                }

                results.AddRange(await table.ExecuteBatchAsync(batch));
            }

            return results;
        }

        public static async Task<TableResult> Merge<T>(string tableName, T entity) where T : class, ITableEntity
        {
            HandleETag(entity);

            var table = GetTable(tableName);
            return await table.ExecuteAsync(TableOperation.Merge(entity));
        }

        public static async Task<TableResult> InsertOrReplace<T>(string tableName, T entity) where T : class, ITableEntity
        {
            HandleETag(entity);

            var table = GetTable(tableName);
            return await table.ExecuteAsync(TableOperation.InsertOrReplace(entity));
        }

        public static async Task<TableResult> Replace<T>(string tableName, T entity) where T : class, ITableEntity
        {
            HandleETag(entity);

            var table = GetTable(tableName);
            return await table.ExecuteAsync(TableOperation.Replace(entity));
        }

        public static async Task<TableResult> Delete<T>(string tableName, T entity) where T : class, ITableEntity
        {
            HandleETag(entity);

            var table = GetTable(tableName);
            return await table.ExecuteAsync(TableOperation.Delete(entity));
        }
    }
}
