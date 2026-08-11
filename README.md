# VisiCore Slack Audit Logs Rest Collector
----

[![License: Apache 2.0][license-badge]][license]

[license-badge]: https://img.shields.io/badge/License-Apache_2.0-blue.svg
[license]: https://github.com/criblio/appscope/blob/master/LICENSE

This pack pulls all audit activity from the Slack Audit Logs API into your data observability pipeline with audit events like user and AI activity.

It establishes a secure, scheduled polling mechanism to programmatically ingest Slack's audit logs (like workspace creation, user logins, and file downloads) ensuring comprehensive visibility into enterprise security and compliance events.

## About this Pack

*   **Targeted Ingestion**: Pre-configured to poll the `/logs` endpoint every 5 minutes.
*   **Granular Visibility**: Captures all **actions** as defined in the [Slack Audit Reference](https://docs.slack.dev/reference/audit-logs-api/methods-actions-reference), including `user_login`, `file_download`, `preference_change`, and AI events, but can be customized to pull specific actions only.
*   Assisted **OAuth2 Token Generation**: Unlike service-level OAuth, Slack requires interactive user consent to install apps, and log collection must be tied to a Slack Owner user account. The Cribl UI provides no way to provide a return URI for interactive consent or to perform this token exchange. This pack and the associated authentication service close these gaps to allow you to collect Slack logs.

To learn more about the Slack Audit Logs API, visit the [official documentation](https://docs.slack.dev/admins/audit-logs-api/) and the [technical API reference](https://docs.slack.dev/reference/audit-logs-api/methods-actions-reference/).

## Required prerequisites

*   You must be on a Slack Enterprise plan
*   The Slack Owner must create a Slack App with the `auditlogs:read` scope for authorization
*   An OAuth2 User Token (starting with `xoxp-`, keep reading for step-by-step instructions to generate this token)

## Generate the OAuth2 User Token

You may obtain your token at VisiCore's [Cribl Slack Authorization](https://portal.visicoretech.com/cribl/slack) page.

![Login Flow](https://static.visicoretech.com/img/content/cc-stream-slack-audit-rest-io/auth_flow_1.v2.png "Login Flow") 

Please read this page carefully. If you agree, click *Add to Slack*.

![Login Flow](https://static.visicoretech.com/img/content/cc-stream-slack-audit-rest-io/auth_flow_2.v3.png "Login Flow")

If you are not already signed into Slack, please do so. Follow the instructions in the Slack consent workflow and reach out to <CriblPacks@visicoretech.com> with any questions.

![Login Flow](https://static.visicoretech.com/img/content/cc-stream-slack-audit-rest-io/auth_flow_3.v2.png "Login Flow")

## Deployment

1. **Install** the pack via Cribl > Stream > Worker Group > Processing > Packs > Add Pack (from the Dispensary).
  - Cribl may try to append the version number to the pack ID. This is designed to be an *upgrade-in-place* pack, so if your pack ID reads anything other than `cc-stream-slack-audit-rest-io`, then change it to that value.
2. From the Packs page, click **Slack Audit Rest Collector**
3. Navigate to **Knowledge** > **Variables** within the Pack.
4. Update `slack_oauth_token` with your Slack **User OAuth Token** (starting with `xoxp-`) retrieved above.
5. (Optional) All other customizable values are also here.
6. **Always** remember to **Commit and Deploy** after changing variables.
7. Celebrate! You now have Slack Audit Logs flowing into your Cribl instance.

## Usage

All operational settings are configured in **Knowledge** > **Variables** inside the pack:

| Variable | Description |
| --- | --- |
| `slack_oauth_token` | Slack User OAuth Token (starting with `xoxp-`). Required. |
| `destination` | Output ID for collected events. Leave blank to use worker group default. See [Destination](#destination). |
| `datatype` | Value used for routing, and for `sourcetype` when Splunk fields are enabled. |
| `enable_splunk_fields` | Set to `true` to populate `index`, `sourcetype`, `source`, and `host`. See [SIEM](#siem). |
| `slack_audit_log_index` | Target index when Splunk fields are enabled (default: `main`). See [SIEM](#siem). |
| `actions` | Comma-separated list of audit action names to collect. Leave empty for all actions. |
| `limit` | Max events requested per API page (default: `100`). |
| `settle_lag_seconds` | Seconds collection window trails the present (default: `300`). See [How Collection Timing Works](#how-collection-timing-works). |
| `lookback_overlap_seconds` | Seconds collection window overlaps past watermark (default: `300`). See [How Collection Timing Works](#how-collection-timing-works). |

Always remember to **Commit and Deploy** after modifying variables.

## How Collection Timing Works

The collector runs every 5 minutes. Two settings control which slice of time each run requests:

*   **Trailing the present (`settle_lag_seconds`)**: A run requests events up to 5 minutes ago rather than "now". Because Slack publishes no availability SLA for when audit logs become queryable, reading right up to the present risks querying an incomplete time slice.
*   **Lookback overlap (`lookback_overlap_seconds`)**: Each run starts its window 5 minutes before the last collected watermark, not at the watermark itself. If a collection run fails or is interrupted midway, the next run covers the uncollected events.

Together, these mean the pack **collects most events twice by design**. The pipeline's Suppress function drops repeats by matching on `id`, so downstream destinations normally receive each event once.

### Tuning Collection Timing

*   **If you need events sooner**: Lower `settle_lag_seconds`. Events reach the destination faster, but events that Slack makes queryable after the lag window will be missed.
*   **If you do not need events quickly**: Increase the collector cron schedule interval, and increase `lookback_overlap_seconds` to match. This yields identical event completeness with fewer API calls and lower rate-limit overhead. Always keep `lookback_overlap_seconds` greater than or equal to the cron interval.

### Repeated Events & Deduplication Contract

Delivery is **at-least-once**. While the pipeline suppresses repeats during continuous collection, duplicate events can still reach the destination in two edge cases:

1.  A quiet period longer than 1 hour (the memory window of the Suppress function).
2.  A Cribl Worker Process restart or rebalance, which resets in-memory suppression state.

The audit log `id` field is unique per event and serves as the idempotency key.

## Destination

By default, installing this pack automatically enables the collector and forwards to the configured default destination for the worker group. There are two options for customizing the destination of a collector in a pack. The simple way is to create a new destination **within the pack** itself, and then update the `destination` variable with the destination output ID. The more complicated way uses the Output Router as a default destination for the worker group allowing you to configure the destination outside of the pack. See [Route to any destination with Cribl Packs using the Output Router](https://cribl.io/blog/the-power-of-an-output-router-as-a-default-destination-in-cribl-packs/) for details on the second approach.

## SIEM

If your System of Analysis supports the `index` metadata field, update the pack variable `slack_audit_log_index` to reflect your target index, and set `enable_splunk_fields` to `true` to enable the index, sourcetype, source, and host fields.

This pack is optionally plug-and-play with the [Slack Add-on for Splunk](https://splunkbase.splunk.com/app/4986) and [Slack Audit App for Splunk](https://splunkbase.splunk.com/app/5013). Note that the app expects an index value of `slack_audit` if you want to avoid customizing the Splunk side. Create the index in Splunk before updating this variable.

## Upgrades

As a better practice, please do not modify sources, routes, or pipelines within the pack. Do not insert this Pack (as a Pipeline) into the global Routes table outside of the Pack. All control is designed to be handled through pack variables. If you need functionality not present in the sources, routes, or pipelines, please reach out to <CriblPacks@visicoretech.com> to log a feature request. Modifying these core items can make upgrades... difficult. For a seamless, Cribl-native way to set non-pack destinations for pack sources, see [The power of an Output Router as a default destination in Cribl Packs](https://cribl.io/blog/the-power-of-an-output-router-as-a-default-destination-in-cribl-packs/).

To upgrade, use the `Upgrade` option through the `Actions` column on the packs page. If you upload/overwrite, it will destroy any variable settings you have configured (like your `slack_oauth_token`).

Upgrading certain Cribl Packs using the same Pack ID can have unintended consequences. See [Upgrading an Existing Pack](https://docs.cribl.io/stream/packs#upgrading) for details.

## Sample Events

See <https://docs.slack.dev/admins/audit-logs-api/>

## Authors

* Paul Stout - <Paul@VisiCoreTech.com>
* Jacob Evans - <jevans@VisiCoreTech.com>  
* Andrew Hendrix - <Andrewh@VisiCoreTech.com>

To contact us, please email <CriblPacks@VisiCoreTech.com>.

## Release Notes

### Version 1.1.0 - 2026-09-16

*   **Duplicate Event Resolution**: Resolved duplicate event collection by introducing a deliberate lookback overlap (`lookback_overlap_seconds`), a settle lag (`settle_lag_seconds`), and in-pipeline Suppress deduplication keyed on `id`.
*   **Cursor Pagination Fixes**: Corrected pagination to advance past page 1 by passing the `cursor` request parameter, fixing `lastPageExpr` nested attribute syntax, and disabling `stopOnEmptyResults`.
*   **Collector & State Resilience**: Protected state tracking against undefined timestamp merges, preserved `date_create` in event payloads, and set default page size to 100.
*   **Validation & Cleanup**: Removed unused OAuth scope, added PR pack validation CI, and added test samples for deduplication edge cases.

### Version 1.0.0 - 2025-12-18

*   **README**: Final cleanup before submission
*   **State Tracking**: Track the timestamp of the last successfully pulled event and start the next collection from it
*   **Default Index**: Changed default index from `slack_audit` to `main` to avoid potential invalid index errors in downstream systems
*   **Data Samples**: Upload distinct data samples for: all actions (small), all actions (large), user activity only, AI activity only
*   **Pipeline cleanup**: Remove unnecessary fields - stick to standard metadata fields only

### Version 0.9.0 - 2025-12-15

*   **README**: Add instructional images for OAuth token generation
*   **Renames**: Rename rest collector and pipeline to lowercase only and no spaces for ease of use with Cribl API
*   **Variables**: Updated rest collector source to be 100% configurable via variables alone
*   **Limits**: Remove all default limits (customizable via variables)

### Version 0.1.0 - 2025-12-10

*   **Turnkey Collection**: Pre-configured REST Collector for the Slack Audit API `/logs` endpoint
*   **Comprehensive Auditing**: Ingests critical audit events like user logins, file downloads, workspace modifications, and more
*   **Smart Pagination**: Automatically handles API pagination to ensure no events are missed during high-volume periods
*   **SIEM Ready**: Optional configuration to match the schema and index expectations of the Slack add-on for Splunk
*   **Standardized Schema**: Delivers consistent JSON event structures ready for downstream analysis or SIEM ingestion

## Contributing to the Pack

To contribute to this Pack, or to report any issues or enhancement requests, please connect with **VisiCore Tech** on [Cribl Community Slack](https://cribl-community.slack.com) or email us at: <CriblPacks@visicoretech.com>.

## License
---
This Pack uses the following license: [`Apache 2.0`](https://github.com/criblio/appscope/blob/master/LICENSE).
