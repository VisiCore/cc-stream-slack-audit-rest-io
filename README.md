# VisiCore Slack Audit Logs Rest Collector

[![Pack validation][ci-badge]][ci-runs]
[![License: Apache 2.0][license-badge]][license]

[ci-badge]: https://github.com/VisiCore/cc-stream-slack-audit-rest-io/actions/workflows/pack-validation.yml/badge.svg
[ci-runs]: https://github.com/VisiCore/cc-stream-slack-audit-rest-io/actions/workflows/pack-validation.yml
[license-badge]: https://img.shields.io/badge/License-Apache_2.0-blue.svg
[license]: https://www.apache.org/licenses/LICENSE-2.0
[output-router]: https://cribl.io/blog/the-power-of-an-output-router-as-a-default-destination-in-cribl-packs/

This pack pulls all audit activity from the Slack Audit Logs API into your data
observability pipeline with audit events like user and AI activity.

It establishes a secure, scheduled polling mechanism to programmatically ingest
Slack's audit logs (like workspace creation, user logins, and file downloads)
ensuring comprehensive visibility into enterprise security and compliance
events.

## About this Pack

* **Targeted Ingestion**: Pre-configured to poll the `/logs` endpoint every 5
  minutes.
* **Granular Visibility**: Captures all **actions** as defined in the
  [Slack Audit Reference](https://docs.slack.dev/reference/audit-logs-api/methods-actions-reference),
  including `user_login`, `file_download`, `preference_change`, and AI events,
  but can be customized to pull specific actions only.
* Assisted **OAuth2 Token Generation**: Unlike service-level OAuth, Slack
  requires interactive user consent to install apps, and log collection must be
  tied to a Slack Owner user account. The Cribl UI provides no way to provide a
  return URI for interactive consent or to perform this token exchange. This
  pack and the associated authentication service close these gaps to allow you
  to collect Slack logs.

To learn more about the Slack Audit Logs API, visit the
[official documentation](https://docs.slack.dev/admins/audit-logs-api/) and the
[technical API reference](https://docs.slack.dev/reference/audit-logs-api/methods-actions-reference/).

## Required prerequisites

* You must be on a Slack Enterprise plan
* The Slack Owner must create a Slack App with the `auditlogs:read` scope for
  authorization
* An OAuth2 User Token (starting with `xoxp-`, keep reading for step-by-step
  instructions to generate this token)

## Generate the OAuth2 User Token

You may obtain your token at VisiCore's
[Cribl Slack Authorization](https://portal.visicoretech.com/cribl/slack) page.

![Login Flow](https://static.visicoretech.com/img/content/cc-stream-slack-audit-rest-io/auth_flow_1.v2.png "Login Flow")

Please read this page carefully. If you agree, click *Add to Slack*.

![Login Flow](https://static.visicoretech.com/img/content/cc-stream-slack-audit-rest-io/auth_flow_2.v3.png "Login Flow")

If you are not already signed into Slack, please do so. Follow the instructions
in the Slack consent workflow and reach out to <CriblPacks@visicoretech.com>
with any questions.

![Login Flow](https://static.visicoretech.com/img/content/cc-stream-slack-audit-rest-io/auth_flow_3.v2.png "Login Flow")

## Installation

1. **Install** the pack via Cribl > Stream > Worker Group > Processing > Packs >
   Add Pack (from the Dispensary).
   Cribl may try to append the version number to the pack ID. This is designed
   to be an *upgrade-in-place* pack, so if your pack ID reads anything other
   than `cc-stream-slack-audit-rest-io`, then change it to that value.
2. From the Packs page, click **Slack Audit Rest Collector**
3. Navigate to **Knowledge** > **Variables** within the Pack.
4. Update `slack_oauth_token` with your Slack **User OAuth Token** (starting
   with `xoxp-`) retrieved above.
5. (Optional) All other customizable values are also here.
6. **Always** remember to **Commit and Deploy** after changing variables.
7. Celebrate! You now have Slack Audit Logs flowing into your Cribl instance.

## Usage

Once installed and configured, the pack runs on its own. The collector polls the
Slack Audit Logs API on a schedule, and the pipeline parses each event, adds
optional metadata fields, and forwards the result to your chosen destination.

Everything you can change lives in **Knowledge** > **Variables** inside the pack:

| Variable | Purpose |
| --- | --- |
| `slack_oauth_token` | Your Slack User OAuth Token. Required. |
| `destination` | Output ID to forward events to. |
| `datatype` | Value used for routing, and for `sourcetype` when Splunk fields are on. |
| `enable_splunk_fields` | Set to `true` to add `index`, `sourcetype`, `source`, and `host`. |
| `slack_audit_log_index` | Target index when Splunk fields are enabled. |
| `actions` | Comma-separated action names to collect. Leave empty for all actions. |
| `limit` | Page size requested from the API. |
| `settle_lag_seconds` | How far behind the present each collection window ends. |
| `lookback_overlap_seconds` | How far back each window starts before the last collected event. |

Commit and Deploy after changing any variable.

## How collection timing works

The collector runs every 5 minutes. Two settings control which slice of time
each run asks for.

**The collector stays 5 minutes behind the present.** A run does not ask for
events up to "now". It asks for events up to 5 minutes ago. Slack does not
promise how quickly an audit event becomes readable through the API, so reading
right up to the present risks asking for a period Slack has not finished
filling. `settle_lag_seconds` controls this gap.

**Each run re-reads the last 5 minutes.** A run starts its window 5 minutes
before the last event it collected, not at that event. If a run fails part way
through, the next run covers the ground it missed. `lookback_overlap_seconds`
controls this overlap.

Together these mean the pack **collects most events twice on purpose**. The
pipeline drops the repeat by matching on the event `id`, so your destination
normally sees each event once.

### If you need events sooner

Lower `settle_lag_seconds`. Events reach your destination faster. The trade-off
is that more events arrive at Slack later than your window, and those are
missed.

### If you do not need events quickly

Raise the collection interval on the schedule, and raise
`lookback_overlap_seconds` to match it. You get the same completeness with fewer
API calls and less rate-limit pressure. Keep the overlap greater than or equal
to the interval, or gaps can open between runs.

### Repeated events

Delivery is **at-least-once**. The pipeline removes repeats it can see, but two
situations can still let one through:

* A quiet period longer than an hour, which is how long the pipeline remembers
  an `id`.
* A Worker Process restart, which clears that memory.

The `id` field is unique per audit event and is the key to deduplicate on. In
Splunk, `| dedup id` is enough. Keep this in mind if you compare event counts
against the Slack API directly.

## Destination

By default, installing this pack automatically enables the collector and
forwards to the configured default destination for the worker group. There are
two options for customizing the destination of a collector in a pack. The simple
way is to create a new destination **within the pack** itself, and then update
the `destination` variable with the destination output ID. The more complicated
way uses the Output Router as a default destination for the worker group
allowing you to configure the destination outside of the pack. See
[Route to any destination with Cribl Packs using the Output Router][output-router]
for details on the second approach.

## SIEM

If your System of Analysis supports the `index` metadata field, update the pack
variable `slack_audit_log_index` to reflect your target index, and set
`enable_splunk_fields` to `true` to enable the index, sourcetype, source, and
host fields.

This pack is optionally plug-and-play with the
[Slack Add-on for Splunk](https://splunkbase.splunk.com/app/4986) and
[Slack Audit App for Splunk](https://splunkbase.splunk.com/app/5013). Note that
the app expects an index value of `slack_audit` if you want to avoid customizing
the Splunk side. Create the index in Splunk before updating this variable.

## Upgrades

As a better practice, please do not modify sources, routes, or pipelines within
the pack. Do not insert this Pack (as a Pipeline) into the global Routes table
outside of the Pack. All control is designed to be handled through pack
variables. If you need functionality not present in the sources, routes, or
pipelines, please reach out to <CriblPacks@visicoretech.com> to log a feature
request. Modifying these core items can make upgrades... difficult. To set
non-pack destinations for pack sources the Cribl-native way, see
[The power of an Output Router as a default destination in Cribl Packs][output-router].

To upgrade, use the `Upgrade` option through the `Actions` column on the packs
page. If you upload/overwrite, it will destroy any variable settings you have
configured (like your `slack_oauth_token`).

Upgrading certain Cribl Packs using the same Pack ID can have unintended
consequences. See
[Upgrading an Existing Pack](https://docs.cribl.io/stream/packs#upgrading) for
details.

## Sample Events

See <https://docs.slack.dev/admins/audit-logs-api/>

## Authors

* Paul Stout - <Paul@VisiCoreTech.com>
* Jacob Evans - <jevans@VisiCoreTech.com>
* Andrew Hendrix - <Andrewh@VisiCoreTech.com>

To contact us, please email <CriblPacks@VisiCoreTech.com>.

## Release Notes

### Version 1.0.0 - 2025-12-18

* **README**: Final cleanup before submission
* **State Tracking**: Track the timestamp of the last successfully pulled event
  and start the next collection from it
* **Default Index**: Changed default index from `slack_audit` to `main` to avoid
  potential invalid index errors in downstream systems
* **Data Samples**: Upload distinct data samples for: all actions (small), all
  actions (large), user activity only, AI activity only
* **Pipeline cleanup**: Remove unnecessary fields - stick to standard metadata
  fields only

### Version 0.9.0 - 2025-12-15

* **README**: Add instructional images for OAuth token generation
* **Renames**: Rename rest collector and pipeline to lowercase only and no
  spaces for ease of use with Cribl API
* **Variables**: Updated rest collector source to be 100% configurable via
  variables alone
* **Limits**: Remove all default limits (customizable via variables)

### Version 0.1.0 - 2025-12-10

* **Turnkey Collection**: Pre-configured REST Collector for the Slack Audit API
  `/logs` endpoint
* **Comprehensive Auditing**: Ingests critical audit events like user logins,
  file downloads, workspace modifications, and more
* **Smart Pagination**: Automatically handles API pagination to ensure no events
  are missed during high-volume periods
* **SIEM Ready**: Optional configuration to match the schema and index
  expectations of the Slack add-on for Splunk
* **Standardized Schema**: Delivers consistent JSON event structures ready for
  downstream analysis or SIEM ingestion

## Contributing

To contribute to this Pack, or to report any issues or enhancement requests,
please connect with **VisiCore Tech** on
[Cribl Community Slack](https://cribl-community.slack.com) or email us at:
<CriblPacks@visicoretech.com>.

## License

This Pack uses the following license:
[`Apache 2.0`](https://www.apache.org/licenses/LICENSE-2.0).
