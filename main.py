#!/usr/bin/env python3
"""Internship Auto-Apply Tool - Main entry point."""

import os
import sys
from pathlib import Path

import click
import yaml

from src.instagram import StoryMonitor
from src.instagram.story_monitor import ManualStoryInput
from src.parser import LinkExtractor
from src.applier import FormFiller
from src.storage import Database


def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file."""
    path = Path(config_path)
    if not path.exists():
        click.echo(f"Error: Config file not found: {config_path}", err=True)
        click.echo("Create a config.yaml file with your settings.", err=True)
        sys.exit(1)

    with open(path) as f:
        return yaml.safe_load(f)


@click.group()
@click.option("--config", "-c", default="config.yaml", help="Path to config file")
@click.pass_context
def cli(ctx, config):
    """Internship Auto-Apply Tool - Monitor stories and auto-fill applications."""
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config
    ctx.obj["config"] = load_config(config)


@cli.command()
@click.pass_context
def check(ctx):
    """Verify Instagram connection and fetch latest stories."""
    config = ctx.obj["config"]
    ig_config = config.get("instagram", {})

    click.echo("Checking Instagram connection...")
    click.echo(f"  Username: {ig_config.get('username', 'Not set')}")
    click.echo(f"  Target accounts: {', '.join(ig_config.get('target_accounts', []))}")

    if not ig_config.get("username") or not ig_config.get("password"):
        click.echo("\nError: Instagram credentials not configured", err=True)
        click.echo("Edit config.yaml and add your Instagram username/password", err=True)
        return

    monitor = StoryMonitor(
        username=ig_config["username"],
        password=ig_config["password"],
        target_accounts=ig_config.get("target_accounts", []),
    )

    # Try to load existing session first
    click.echo("\nAttempting to load saved session...")
    if monitor.load_session():
        click.echo("  Session loaded successfully")
    else:
        click.echo("  No saved session, logging in...")
        if monitor.login():
            click.echo("  Login successful")
            monitor.save_session()
            click.echo("  Session saved for future use")
        else:
            click.echo("  Login failed", err=True)
            return

    # Check connection status
    status = monitor.check_connection()
    click.echo(f"\nConnection status:")
    click.echo(f"  Logged in: {status['logged_in']}")

    if status["accounts_accessible"]:
        click.echo(f"\nAccessible accounts:")
        for acc in status["accounts_accessible"]:
            click.echo(f"  - @{acc['username']} ({acc['followers']} followers)")
            if acc["is_private"]:
                click.echo("    (Private account)")

    if status["errors"]:
        click.echo(f"\nErrors:")
        for error in status["errors"]:
            click.echo(f"  - {error}", err=True)


@cli.command()
@click.pass_context
def fetch(ctx):
    """Fetch stories and extract job links."""
    config = ctx.obj["config"]
    ig_config = config.get("instagram", {})
    db = Database()
    extractor = LinkExtractor()

    click.echo("Fetching stories...")

    monitor = StoryMonitor(
        username=ig_config.get("username", ""),
        password=ig_config.get("password", ""),
        target_accounts=ig_config.get("target_accounts", []),
    )

    # Try to load session or login
    if not monitor.load_session():
        if not monitor.login():
            click.echo("Login failed. Use 'add' command for manual URL input.", err=True)
            return
        monitor.save_session()

    stories = monitor.fetch_stories()
    click.echo(f"Found {len(stories)} stories with URLs")

    new_links = 0
    for story in stories:
        for url in story.urls:
            # Process and check if it's a job link
            resolved = extractor.process_url(url)
            if resolved.is_job_link:
                link_id = db.add_link(
                    url=resolved.original_url,
                    source_account=story.account,
                    story_timestamp=story.timestamp.isoformat(),
                    resolved_url=resolved.final_url,
                )
                if link_id:
                    new_links += 1
                    db.update_link_info(
                        link_id=link_id,
                        platform=resolved.platform,
                        company_name=resolved.company_hint,
                    )
                    click.echo(f"  New: {resolved.final_url}")
                    if resolved.company_hint:
                        click.echo(f"       Company: {resolved.company_hint}")

    click.echo(f"\nAdded {new_links} new job links")


@cli.command()
@click.argument("url")
@click.option("--account", "-a", default="manual", help="Source account name")
@click.pass_context
def add(ctx, url, account):
    """Manually add a job application URL."""
    db = Database()
    extractor = LinkExtractor()

    click.echo(f"Processing URL: {url}")
    resolved = extractor.process_url(url)

    click.echo(f"  Final URL: {resolved.final_url}")
    click.echo(f"  Platform: {resolved.platform or 'Unknown'}")
    click.echo(f"  Company hint: {resolved.company_hint or 'Unknown'}")
    click.echo(f"  Is job link: {resolved.is_job_link}")

    link_id = db.add_link(
        url=resolved.original_url,
        source_account=account,
        resolved_url=resolved.final_url,
    )

    if link_id:
        db.update_link_info(
            link_id=link_id,
            platform=resolved.platform,
            company_name=resolved.company_hint,
        )
        click.echo(f"\nLink added with ID: {link_id}")
    else:
        click.echo("\nLink already exists in database")


@cli.command("list")
@click.option("--status", "-s", default=None, help="Filter by status (new, applied, skipped)")
@click.pass_context
def list_links(ctx, status):
    """Show extracted internship links."""
    db = Database()
    links = db.get_all_links(status=status)

    if not links:
        click.echo("No links found.")
        if status:
            click.echo(f"(filtered by status: {status})")
        return

    click.echo(f"Found {len(links)} links:")
    click.echo("-" * 60)

    for link in links:
        click.echo(f"\nID: {link['id']} | Status: {link['status']}")
        click.echo(f"URL: {link['resolved_url'] or link['url']}")
        if link["company_name"]:
            click.echo(f"Company: {link['company_name']}")
        if link["platform"]:
            click.echo(f"Platform: {link['platform']}")
        click.echo(f"Source: @{link['source_account']} | {link['discovered_at']}")


@cli.command()
@click.pass_context
def stats(ctx):
    """Show application statistics."""
    db = Database()
    stats = db.get_stats()

    click.echo("Application Statistics")
    click.echo("=" * 40)

    click.echo("\nLinks by status:")
    for status, count in stats.get("links_by_status", {}).items():
        click.echo(f"  {status}: {count}")

    click.echo(f"\nTotal applications submitted: {stats.get('total_applications', 0)}")


@cli.command()
@click.option("--link-id", "-l", type=int, help="Apply to specific link ID")
@click.option("--headless/--no-headless", default=False, help="Run browser in headless mode")
@click.pass_context
def apply(ctx, link_id, headless):
    """Start semi-automatic application process with review."""
    config = ctx.obj["config"]
    db = Database()
    profile = config.get("profile", {})

    if link_id:
        links = [l for l in db.get_all_links() if l["id"] == link_id]
    else:
        links = db.get_new_links()

    if not links:
        click.echo("No new links to apply to.")
        return

    click.echo(f"Found {len(links)} links to process")
    click.echo("-" * 60)

    filler = FormFiller(profile=profile, headless=headless)

    try:
        filler.start_browser()

        for link in links:
            url = link["resolved_url"] or link["url"]
            click.echo(f"\n{'='*60}")
            click.echo(f"Processing: {url}")
            if link["company_name"]:
                click.echo(f"Company: {link['company_name']}")
            click.echo(f"Platform: {link['platform'] or 'Unknown'}")

            # Analyze the form
            click.echo("\nAnalyzing form...")
            try:
                analysis = filler.analyze_form(url)
            except Exception as e:
                click.echo(f"Error analyzing form: {e}", err=True)
                continue

            if analysis.requires_login:
                click.echo("This form requires login/account creation.")
                click.echo("Please complete login manually in the browser.")
                filler.wait_for_user_action()
                # Re-analyze after login
                analysis = filler.analyze_form(filler._page.url)

            # Show what would be filled
            click.echo(f"\nDetected {len(analysis.fields)} fillable fields:")
            for field in analysis.fields[:10]:  # Show first 10
                click.echo(f"  - {field.selector}: {field.value}")

            if len(analysis.fields) > 10:
                click.echo(f"  ... and {len(analysis.fields) - 10} more")

            click.echo(f"\nFile uploads: {len(analysis.file_uploads)}")
            for upload in analysis.file_uploads:
                click.echo(f"  - {upload['type']}: {upload['file_path'] or 'Not configured'}")

            # User review
            click.echo("\n" + "-" * 40)
            action = click.prompt(
                "Action",
                type=click.Choice(["fill", "skip", "manual", "quit"]),
                default="fill",
            )

            if action == "quit":
                break
            elif action == "skip":
                db.update_link_status(link["id"], "skipped")
                click.echo("Skipped.")
                continue
            elif action == "manual":
                click.echo("Opening browser for manual entry...")
                click.echo("Press Enter when done.")
                filler.wait_for_user_action()
                if click.confirm("Mark as applied?"):
                    db.record_application(link["id"], notes="Manual application")
                continue

            # Fill the form
            click.echo("\nFilling form...")
            result = filler.fill_form(analysis, dry_run=False)

            for filled_field in result["fields"]:
                click.echo(f"  Filled: {filled_field['selector']}")

            for uploaded in result["files"]:
                click.echo(f"  Uploaded: {uploaded['type']}")

            if result["errors"]:
                click.echo("\nErrors:")
                for error in result["errors"]:
                    click.echo(f"  - {error}", err=True)

            # Final review before submit
            click.echo("\n" + "-" * 40)
            click.echo("Form filled. Please review in the browser.")

            submit_action = click.prompt(
                "Submit?",
                type=click.Choice(["submit", "edit", "skip"]),
                default="edit",
            )

            if submit_action == "submit":
                if not config.get("settings", {}).get("auto_submit", False):
                    if not click.confirm("Confirm submission?"):
                        continue

                if filler.submit_form(analysis):
                    click.echo("Submitted successfully!")
                    db.record_application(link["id"])
                else:
                    click.echo("Submit may have failed. Check browser.", err=True)
                    filler.wait_for_user_action()

            elif submit_action == "edit":
                click.echo("Make your edits in the browser.")
                filler.wait_for_user_action()
                if click.confirm("Mark as applied?"):
                    db.record_application(link["id"], notes="Manually edited before submit")

            else:
                db.update_link_status(link["id"], "skipped")

    finally:
        filler.stop_browser()

    click.echo("\nDone!")


@cli.command()
@click.option("--port", "-p", default=9222, help="Chrome debugging port")
@click.pass_context
def fill(ctx, port):
    """Fill the form in your current browser tab.

    First, start Chrome with remote debugging:
      /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222

    Then navigate to the job application page and run:
      python main.py fill
    """
    config = ctx.obj["config"]
    profile = config.get("profile", {})

    click.echo(f"Connecting to Chrome on port {port}...")

    filler = FormFiller(profile=profile)

    if not filler.connect_to_browser(f"http://localhost:{port}"):
        click.echo("\nTo use this command, start Chrome with debugging enabled:")
        click.echo(f"  /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port={port}")
        click.echo("\nOr on Linux:")
        click.echo(f"  google-chrome --remote-debugging-port={port}")
        return

    try:
        click.echo(f"Connected! Current page: {filler._page.url}")
        click.echo("\nAnalyzing form...")

        analysis = filler.analyze_current_page()

        click.echo(f"Platform: {analysis.platform or 'Unknown'}")
        click.echo(f"\nDetected {len(analysis.fields)} fillable fields:")
        for field in analysis.fields:
            click.echo(f"  - {field.label or field.selector}: {field.value}")

        click.echo(f"\nFile uploads: {len(analysis.file_uploads)}")
        for upload in analysis.file_uploads:
            status = "Ready" if upload["file_path"] else "No file configured"
            click.echo(f"  - {upload['label'] or upload['type']}: {status}")

        if not analysis.fields and not analysis.file_uploads:
            click.echo("\nNo fillable fields detected on this page.")
            click.echo("Make sure you're on the application form page.")
            return

        action = click.prompt(
            "\nAction",
            type=click.Choice(["fill", "quit"]),
            default="fill",
        )

        if action == "fill":
            click.echo("\nFilling form...")
            result = filler.fill_form(analysis, dry_run=False)

            click.echo(f"\nFilled {len(result['fields'])} fields:")
            for filled in result["fields"]:
                click.echo(f"  {filled['label'] or filled['selector']}: {filled['value']}")

            if result["files"]:
                click.echo(f"\nUploaded {len(result['files'])} files:")
                for f in result["files"]:
                    click.echo(f"  {f['type']}: {f['file']}")

            if result["errors"]:
                click.echo("\nErrors:")
                for error in result["errors"]:
                    click.echo(f"  - {error}", err=True)

            click.echo("\nDone! Review the form in your browser.")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
    finally:
        filler.stop_browser()


@cli.command()
@click.argument("url")
@click.pass_context
def test(ctx, url):
    """Test form filling on a URL (opens new browser)."""
    config = ctx.obj["config"]
    profile = config.get("profile", {})

    click.echo(f"Testing form fill on: {url}")
    click.echo("-" * 60)

    filler = FormFiller(profile=profile, headless=False)

    try:
        filler.start_browser()

        click.echo("Analyzing form...")
        analysis = filler.analyze_form(url)

        click.echo(f"Platform: {analysis.platform or 'Unknown'}")
        click.echo(f"Requires login: {analysis.requires_login}")

        if analysis.requires_login:
            click.echo("\nThis form requires login/account creation.")
            click.echo("Complete login in the browser, then press Enter.")
            filler.wait_for_user_action()
            analysis = filler.analyze_form(filler._page.url)

        click.echo(f"\nDetected {len(analysis.fields)} fillable fields:")
        for field in analysis.fields:
            click.echo(f"  - {field.selector}: {field.value}")

        click.echo(f"\nFile uploads: {len(analysis.file_uploads)}")
        for upload in analysis.file_uploads:
            click.echo(f"  - {upload['type']}: {upload['file_path'] or 'Not configured'}")

        if analysis.submit_button:
            click.echo(f"\nSubmit button: {analysis.submit_button}")

        action = click.prompt(
            "\nAction",
            type=click.Choice(["fill", "manual", "quit"]),
            default="fill",
        )

        if action == "fill":
            click.echo("\nFilling form...")
            result = filler.fill_form(analysis, dry_run=False)

            for filled in result["fields"]:
                click.echo(f"  Filled: {filled['selector']}")
            for uploaded in result["files"]:
                click.echo(f"  Uploaded: {uploaded['type']}")
            if result["errors"]:
                for error in result["errors"]:
                    click.echo(f"  Error: {error}", err=True)

            click.echo("\nForm filled. Review in browser.")
            click.echo("Press Enter when done.")
            filler.wait_for_user_action()

        elif action == "manual":
            click.echo("Browser open for manual testing. Press Enter when done.")
            filler.wait_for_user_action()

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
    finally:
        filler.stop_browser()

    click.echo("Done!")


@cli.command()
@click.pass_context
def applications(ctx):
    """Show submitted applications."""
    db = Database()
    apps = db.get_applications()

    if not apps:
        click.echo("No applications submitted yet.")
        return

    click.echo(f"Submitted {len(apps)} applications:")
    click.echo("=" * 60)

    for app in apps:
        click.echo(f"\n{app['company_name'] or 'Unknown Company'}")
        click.echo(f"  URL: {app['url']}")
        click.echo(f"  Platform: {app['platform'] or 'Unknown'}")
        click.echo(f"  Applied: {app['applied_at']}")
        if app["notes"]:
            click.echo(f"  Notes: {app['notes']}")


if __name__ == "__main__":
    cli()
