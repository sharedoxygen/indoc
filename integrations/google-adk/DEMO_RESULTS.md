# inDoc + Gemini ADK connector: two-user demo results

- Run started (UTC): 2026-10-11T15:57:46+00:00
- Mode: deployed
- Google Cloud project / region: indoc-511303 / us-central1
- Model: gemini-2.5-flash
- ADK version: 2.11.0
- MCP endpoint host: research.sharedoxygen.com
- Agent Runtime resource: `projects/508662352118/locations/us-central1/reasoningEngines/45608017198055424`

Question asked by both users: **What are the termination terms in our vendor contracts?**

## Checks

| Check | Result | Evidence |
|---|---|---|
| Manager answer cites documents the analyst cannot read | PASS | 705c3ebf-4476-47b5-89cd-f43ca66a88d8, 7e63388f-1366-4fb0-a8ea-86f3ed1b3be0 |
| Analyst received no restricted ids or contract text | PASS | none |
| Both users' agents searched inDoc | PASS | manager: 3 tool call(s); analyst: 1 tool call(s) |

Restricted ids are not assumed: after both runs, every document id either agent saw is read over MCP with the analyst's token, and inDoc's answer decides (verifier calls are audited with client `demo-verifier`). Refused to the analyst: 705c3ebf-4476-47b5-89cd-f43ca66a88d8, 7e63388f-1366-4fb0-a8ea-86f3ed1b3be0.

## Manager (manager.demo@example.com)

Tool calls:

- `search_documents` {'query': 'termination terms vendor contracts'}
- `read_document` {'document_id': '705c3ebf-4476-47b5-89cd-f43ca66a88d8'}
- `read_document` {'document_id': '7e63388f-1366-4fb0-a8ea-86f3ed1b3be0'}

Answer:

Termination terms vary by contract.

*   **Software Subscription Agreement - Brightline Analytics** (id 705c3ebf-4476-47b5-89cd-f43ca66a88d8)
    *   The initial term is twelve months and automatically renews for successive twelve-month terms unless either party gives 60 days' notice of non-renewal.
    *   After the initial term, the Customer may terminate for convenience with 60 days' written notice; prepaid fees are non-refundable, unless the Vendor terminates for convenience, in which case prepaid fees are refunded pro rata.
    *   The Vendor may suspend service if undisputed fees are over 45 days overdue and may terminate if non-payment is not cured within 15 days of a suspension notice.
    *   For 45 days after termination, the Customer may export its data in CSV or Parquet format at no charge.
*   **Master Services Agreement - Halvorsen Freight** (id 7e63388f-1366-4fb0-a8ea-86f3ed1b3be0)
    *   The term is three years from the effective date.
    *   Either party may terminate for convenience on 90 days' written notice; if the Customer terminates for convenience, an early termination fee equal to 15% of the remaining minimum annual commitment applies.
    *   Either party may terminate for material breach that remains uncured 30 days after written notice.
    *   Either party may terminate immediately if the other becomes insolvent.
    *   Upon termination, the Vendor must return or destroy Customer data within 30 days and provide transition assistance for up to 60 days at current rates.

## Analyst (analyst.demo@example.com)

Tool calls:

- `search_documents` {'query': 'termination terms vendor contracts'}

Answer:

I found no documents available to this user that answer the question.

Tokens are short-lived, per user, and not recorded here. Demo data is synthetic.
