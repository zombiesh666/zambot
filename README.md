https://github.com/zombiesh666/zambot

https://docs.api.dashplatform.com/
https://apps.daysmartrecreation.com/dash/x/#/online/chaparralice/calendar
https://apps.daysmartrecreation.com/dash/x/#/online/iceandfield/calendar
https://the-pond-hockey-club.myshopify.com/collections

https://api.daysmartrecreation.com/v1/events?cache[save]=false&company=iceandfield&page[size]=100&page[number]=1&filter[start__gte]=2026-06-13%2000%3A00%3A00&filter[start__lte]=2026-09-01%2023%3A59%3A59&filter[or][0][eventType.code]=10&filter[or][1][eventType.code]=12&filter[or][2][eventType.code]=15&filter[or][3][eventType.code]=16&filter[or][4][eventType.code]=17&filter[or][5][eventType.code]=22&filter[or][6][eventType.code]=g&filter[or][7][eventType.code]=r&include=eventType%2Csummary%2Cresource.facility
https://api.daysmartrecreation.com/v1/events?cache[save]=false&page[size]=100&sort=start&company=chaparralice&filter[start__gte]=2026-06-13%2000%3A00%3A00&filter[start__lte]=2026-06-13%2023%3A59%3A59&filter[or][0][eventType.code]=13&filter[or][1][eventType.code]=g&filter[or][2][eventType.code]=9&filter[or][3][eventType.code]=12&filter[or][4][eventType.code]=6&filter[or][5][eventType.code]=r&include=eventType%2Csummary%2Cresource.facility
https://api.daysmartrecreation.com/v1/events?cache[save]=false&company=iceandfield&filter[id]=3725&include=eventType%2Csummary%2Cresource.facility

Invoke-RestMethod -Method Post -Uri http://localhost:8000/sync
Invoke-RestMethod -Method Post -Uri http://198.199.79.12:8000/sync