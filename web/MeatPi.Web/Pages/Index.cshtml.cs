using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.Extensions.Logging;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using MeatPi.Web.Tables;
using Microsoft.Azure.Cosmos.Table;

namespace MeatPi.Web.Pages
{
    public class IndexModel : PageModel
    {
        public class Cook
        {
            public string DeviceId { get; set; }
            public string CookId { get; set; }
            public string StartTime { get; set; }
            public string LastTime { get; set; }

            internal static Cook FromTable(CookTable cook)
            {
                return new Cook
                {
                    DeviceId = cook.DeviceId,
                    CookId = cook.CookId,
                    StartTime = cook.StartTime,
                    LastTime = cook.LastTime
                };
            }
        }

        private readonly ILogger<IndexModel> _logger;

        public IndexModel(ILogger<IndexModel> logger)
        {
            _logger = logger;
        }

        public async Task OnGet()
        {
            // get all the cooks in the last year
            var condition = TableQuery.GenerateFilterConditionForDate(AzureTableHelper.Timestamp, QueryComparisons.GreaterThan, new DateTimeOffset(DateTime.Today.AddYears(-1)));
            var rows = await AzureTableHelper.Query<CookTable>(CookTable.TableName, condition);

            Cooks = rows.Select(c=> Cook.FromTable(c)).OrderByDescending(c=>c.LastTime);
        }

        public IEnumerable<Cook> Cooks { get; private set; }
    }
}
