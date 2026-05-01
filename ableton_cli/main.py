"""Ableton Live CLI – control Ableton via the AbletonMCP Remote Script."""

import json
import sys
from typing import Any

import click

from ableton_cli.connection import AbletonConnection

# ── Shared helpers ──────────────────────────────────────────────────

_conn: AbletonConnection | None = None


def _get_conn(ctx: click.Context) -> AbletonConnection:
    global _conn
    if _conn is None:
        host = ctx.obj["host"]
        port = ctx.obj["port"]
        _conn = AbletonConnection(host, port)
        try:
            _conn.connect()
        except Exception as e:
            click.echo(f"Error: Ableton に接続できません ({host}:{port}) – {e}", err=True)
            sys.exit(1)
    return _conn


def _pp(data: dict | list) -> None:
    """Pretty-print JSON data."""
    click.echo(json.dumps(data, indent=2, ensure_ascii=False))


# ── Root group ──────────────────────────────────────────────────────

@click.group()
@click.option("--host", default="localhost", help="Ableton Remote Script host")
@click.option("--port", default=9877, type=int, help="Ableton Remote Script port")
@click.pass_context
def cli(ctx: click.Context, host: str, port: int) -> None:
    """Ableton Live CLI – control Ableton from your terminal."""
    ctx.ensure_object(dict)
    ctx.obj["host"] = host
    ctx.obj["port"] = port


# ── Session commands ────────────────────────────────────────────────

@cli.command()
@click.pass_context
def session(ctx: click.Context) -> None:
    """Show current session info (tempo, tracks, etc.)."""
    conn = _get_conn(ctx)
    result = conn.send_command("get_session_info")
    _pp(result)


@cli.command()
@click.argument("bpm", type=float)
@click.pass_context
def tempo(ctx: click.Context, bpm: float) -> None:
    """Set the session tempo (BPM)."""
    conn = _get_conn(ctx)
    conn.send_command("set_tempo", {"tempo": bpm})
    click.echo(f"Tempo set to {bpm} BPM")


@cli.command()
@click.pass_context
def play(ctx: click.Context) -> None:
    """Start playback."""
    conn = _get_conn(ctx)
    conn.send_command("start_playback")
    click.echo("Playback started")


@cli.command()
@click.pass_context
def stop(ctx: click.Context) -> None:
    """Stop playback."""
    conn = _get_conn(ctx)
    conn.send_command("stop_playback")
    click.echo("Playback stopped")


# ── Track commands ──────────────────────────────────────────────────

@cli.group()
def track() -> None:
    """Track operations (info, create, rename)."""
    pass


@track.command("info")
@click.argument("index", type=int)
@click.pass_context
def track_info(ctx: click.Context, index: int) -> None:
    """Show detailed info for a track by INDEX."""
    conn = _get_conn(ctx)
    result = conn.send_command("get_track_info", {"track_index": index})
    _pp(result)


@track.command("create")
@click.option("--index", "-i", default=-1, type=int, help="Insert position (-1 = end)")
@click.pass_context
def track_create(ctx: click.Context, index: int) -> None:
    """Create a new MIDI track."""
    conn = _get_conn(ctx)
    result = conn.send_command("create_midi_track", {"index": index})
    click.echo(f"Created MIDI track: {result.get('name', '?')} (index {result.get('index', '?')})")


@track.command("rename")
@click.argument("index", type=int)
@click.argument("name")
@click.pass_context
def track_rename(ctx: click.Context, index: int, name: str) -> None:
    """Rename a track at INDEX to NAME."""
    conn = _get_conn(ctx)
    result = conn.send_command("set_track_name", {"track_index": index, "name": name})
    click.echo(f"Track renamed to: {result.get('name', name)}")


@track.command("mute")
@click.argument("index", type=int)
@click.pass_context
def track_mute(ctx: click.Context, index: int) -> None:
    """Mute a track at INDEX."""
    conn = _get_conn(ctx)
    conn.send_command("set_track_mute", {"track_index": index, "mute": True})
    click.echo(f"Track {index} muted")


@track.command("unmute")
@click.argument("index", type=int)
@click.pass_context
def track_unmute(ctx: click.Context, index: int) -> None:
    """Unmute a track at INDEX."""
    conn = _get_conn(ctx)
    conn.send_command("set_track_mute", {"track_index": index, "mute": False})
    click.echo(f"Track {index} unmuted")


@track.command("solo")
@click.argument("index", type=int)
@click.pass_context
def track_solo(ctx: click.Context, index: int) -> None:
    """Solo a track at INDEX."""
    conn = _get_conn(ctx)
    conn.send_command("set_track_solo", {"track_index": index, "solo": True})
    click.echo(f"Track {index} soloed")


@track.command("unsolo")
@click.argument("index", type=int)
@click.pass_context
def track_unsolo(ctx: click.Context, index: int) -> None:
    """Unsolo a track at INDEX."""
    conn = _get_conn(ctx)
    conn.send_command("set_track_solo", {"track_index": index, "solo": False})
    click.echo(f"Track {index} unsoloed")


@track.command("volume")
@click.argument("index", type=int)
@click.argument("value", type=float)
@click.pass_context
def track_volume(ctx: click.Context, index: int, value: float) -> None:
    """Set track volume (0.0–1.0; 0.85 ≈ 0 dB)."""
    conn = _get_conn(ctx)
    result = conn.send_command("set_track_volume", {"track_index": index, "volume": value})
    click.echo(f"Track {index} volume set to {result.get('volume', value):.3f}")


@track.command("pan")
@click.argument("index", type=int)
@click.argument("value", type=float)
@click.pass_context
def track_pan(ctx: click.Context, index: int, value: float) -> None:
    """Set track panning (-1.0 = left, 0.0 = center, 1.0 = right)."""
    conn = _get_conn(ctx)
    result = conn.send_command("set_track_pan", {"track_index": index, "pan": value})
    click.echo(f"Track {index} pan set to {result.get('pan', value):.3f}")


# ── Clip commands ───────────────────────────────────────────────────

@cli.group()
def clip() -> None:
    """Clip operations (create, rename, add-notes, fire, stop)."""
    pass


@clip.command("create")
@click.argument("track_index", type=int)
@click.argument("clip_index", type=int)
@click.option("--length", "-l", default=4.0, type=float, help="Clip length in beats")
@click.pass_context
def clip_create(ctx: click.Context, track_index: int, clip_index: int, length: float) -> None:
    """Create a MIDI clip at TRACK_INDEX / CLIP_INDEX."""
    conn = _get_conn(ctx)
    conn.send_command("create_clip", {
        "track_index": track_index,
        "clip_index": clip_index,
        "length": length,
    })
    click.echo(f"Created clip at track {track_index}, slot {clip_index} ({length} beats)")


@clip.command("rename")
@click.argument("track_index", type=int)
@click.argument("clip_index", type=int)
@click.argument("name")
@click.pass_context
def clip_rename(ctx: click.Context, track_index: int, clip_index: int, name: str) -> None:
    """Rename a clip at TRACK_INDEX / CLIP_INDEX."""
    conn = _get_conn(ctx)
    conn.send_command("set_clip_name", {
        "track_index": track_index,
        "clip_index": clip_index,
        "name": name,
    })
    click.echo(f"Clip renamed to: {name}")


@clip.command("add-notes")
@click.argument("track_index", type=int)
@click.argument("clip_index", type=int)
@click.argument("notes_json")
@click.pass_context
def clip_add_notes(ctx: click.Context, track_index: int, clip_index: int, notes_json: str) -> None:
    """Add MIDI notes to a clip. NOTES_JSON is a JSON array of note objects.

    Each note: {"pitch": 60, "start_time": 0.0, "duration": 0.25, "velocity": 100, "mute": false}

    Example: ableton clip add-notes 0 0 '[{"pitch":60,"start_time":0,"duration":1,"velocity":100}]'
    """
    conn = _get_conn(ctx)
    try:
        notes = json.loads(notes_json)
    except json.JSONDecodeError as e:
        click.echo(f"Error: invalid JSON – {e}", err=True)
        sys.exit(1)
    if not isinstance(notes, list):
        click.echo("Error: NOTES_JSON must be a JSON array", err=True)
        sys.exit(1)
    conn.send_command("add_notes_to_clip", {
        "track_index": track_index,
        "clip_index": clip_index,
        "notes": notes,
    })
    click.echo(f"Added {len(notes)} note(s) to track {track_index}, slot {clip_index}")


@clip.command("get-notes")
@click.argument("track_index", type=int)
@click.argument("clip_index", type=int)
@click.pass_context
def clip_get_notes(ctx: click.Context, track_index: int, clip_index: int) -> None:
    """Get MIDI notes from a clip at TRACK_INDEX / CLIP_INDEX."""
    conn = _get_conn(ctx)
    result = conn.send_command("get_clip_notes", {"track_index": track_index, "clip_index": clip_index})
    _pp(result)


@clip.command("duplicate")
@click.argument("track_index", type=int)
@click.argument("clip_index", type=int)
@click.argument("dest_slot", type=int)
@click.pass_context
def clip_duplicate(ctx: click.Context, track_index: int, clip_index: int, dest_slot: int) -> None:
    """Duplicate a clip to DEST_SLOT on the same track."""
    conn = _get_conn(ctx)
    conn.send_command("duplicate_clip", {
        "track_index": track_index,
        "clip_index": clip_index,
        "dest_clip_index": dest_slot,
    })
    click.echo(f"Duplicated clip from slot {clip_index} to slot {dest_slot} on track {track_index}")


@clip.command("fire")
@click.argument("track_index", type=int)
@click.argument("clip_index", type=int)
@click.pass_context
def clip_fire(ctx: click.Context, track_index: int, clip_index: int) -> None:
    """Fire (start playing) a clip."""
    conn = _get_conn(ctx)
    conn.send_command("fire_clip", {"track_index": track_index, "clip_index": clip_index})
    click.echo(f"Fired clip at track {track_index}, slot {clip_index}")


@clip.command("stop")
@click.argument("track_index", type=int)
@click.argument("clip_index", type=int)
@click.pass_context
def clip_stop(ctx: click.Context, track_index: int, clip_index: int) -> None:
    """Stop a clip."""
    conn = _get_conn(ctx)
    conn.send_command("stop_clip", {"track_index": track_index, "clip_index": clip_index})
    click.echo(f"Stopped clip at track {track_index}, slot {clip_index}")


# ── Browser commands ────────────────────────────────────────────────

@cli.group()
def browser() -> None:
    """Browse Ableton's instrument / effect library."""
    pass


@browser.command("tree")
@click.option("--category", "-c", default="all",
              type=click.Choice(["all", "instruments", "sounds", "drums", "audio_effects", "midi_effects"]),
              help="Category to show")
@click.pass_context
def browser_tree(ctx: click.Context, category: str) -> None:
    """Show the browser category tree."""
    conn = _get_conn(ctx)
    result = conn.send_command("get_browser_tree", {"category_type": category})

    for cat in result.get("categories", []):
        _print_tree(cat)


def _print_tree(item: dict, indent: int = 0) -> None:
    prefix = "  " * indent
    name = item.get("name", "?")
    uri = item.get("uri", "")
    marker = "📁" if item.get("is_folder") else ("🎹" if item.get("is_loadable") else "·")
    line = f"{prefix}{marker} {name}"
    if uri:
        line += f"  ({uri})"
    click.echo(line)
    for child in item.get("children", []):
        _print_tree(child, indent + 1)


@browser.command("get")
@click.option("--uri", "-u", default=None, help="URI of the browser item")
@click.option("--path", "-p", default=None, help="Path to the browser item (e.g. 'instruments/Synths/Bass')")
@click.pass_context
def browser_get(ctx: click.Context, uri: str | None, path: str | None) -> None:
    """Get details of a single browser item by URI or path."""
    if not uri and not path:
        click.echo("Error: --uri or --path のどちらかを指定してください", err=True)
        sys.exit(1)
    conn = _get_conn(ctx)
    params: dict[str, Any] = {}
    if uri:
        params["uri"] = uri
    if path:
        params["path"] = path
    result = conn.send_command("get_browser_item", params)
    if result.get("found"):
        _pp(result.get("item", {}))
    else:
        error = result.get("error", "Item not found")
        click.echo(f"Not found: {error}", err=True)
        sys.exit(1)


@browser.command("items")
@click.argument("path")
@click.pass_context
def browser_items(ctx: click.Context, path: str) -> None:
    """List browser items at PATH (e.g. 'instruments/Synths')."""
    conn = _get_conn(ctx)
    result = conn.send_command("get_browser_items_at_path", {"path": path})

    if "error" in result:
        click.echo(f"Error: {result['error']}", err=True)
        sys.exit(1)

    items = result.get("items", [])
    if not items:
        click.echo("No items found.")
        return

    for item in items:
        marker = "📁" if item.get("is_folder") else ("🎹" if item.get("is_loadable") else "·")
        uri = item.get("uri", "")
        line = f"  {marker} {item.get('name', '?')}"
        if uri:
            line += f"  ({uri})"
        click.echo(line)


# ── Load commands ───────────────────────────────────────────────────

@cli.command("load")
@click.argument("track_index", type=int)
@click.argument("uri")
@click.pass_context
def load_instrument(ctx: click.Context, track_index: int, uri: str) -> None:
    """Load an instrument or effect onto a track by URI."""
    conn = _get_conn(ctx)
    result = conn.send_command("load_browser_item", {
        "track_index": track_index,
        "item_uri": uri,
    })
    if result.get("loaded"):
        click.echo(f"Loaded '{result.get('item_name', uri)}' on track {track_index}")
    else:
        click.echo(f"Failed to load: {uri}", err=True)


@cli.command("load-slot")
@click.argument("track_index", type=int)
@click.argument("clip_index", type=int)
@click.argument("uri")
@click.pass_context
def load_slot(ctx: click.Context, track_index: int, clip_index: int, uri: str) -> None:
    """Load a browser item onto a specific Session View clip slot."""
    conn = _get_conn(ctx)
    result = conn.send_command("load_browser_item_to_slot", {
        "track_index": track_index,
        "clip_index": clip_index,
        "item_uri": uri,
    })
    if result.get("loaded"):
        item_name = result.get("item_name", uri)
        click.echo(f"Loaded '{item_name}' on track {track_index}, slot {clip_index}")
    else:
        click.echo(f"Failed to load: {uri}", err=True)


@cli.command("load-drum-kit")
@click.argument("track_index", type=int)
@click.argument("rack_uri")
@click.argument("kit_path")
@click.pass_context
def load_drum_kit(ctx: click.Context, track_index: int, rack_uri: str, kit_path: str) -> None:
    """Load a drum rack and kit onto a track.

    RACK_URI: URI of the drum rack.
    KIT_PATH: Browser path to the drum kit (e.g. 'drums/acoustic/kit1').
    """
    conn = _get_conn(ctx)

    # Step 1: Load the drum rack
    result = conn.send_command("load_browser_item", {
        "track_index": track_index,
        "item_uri": rack_uri,
    })
    if not result.get("loaded"):
        click.echo(f"Failed to load drum rack: {rack_uri}", err=True)
        sys.exit(1)

    # Step 2: Find loadable kits at the path
    kit_result = conn.send_command("get_browser_items_at_path", {"path": kit_path})
    if "error" in kit_result:
        click.echo(f"Drum rack loaded, but kit not found: {kit_result['error']}", err=True)
        sys.exit(1)

    loadable = [i for i in kit_result.get("items", []) if i.get("is_loadable")]
    if not loadable:
        click.echo(f"No loadable drum kits found at '{kit_path}'", err=True)
        sys.exit(1)

    # Step 3: Load the first kit
    kit_uri = loadable[0].get("uri")
    conn.send_command("load_browser_item", {
        "track_index": track_index,
        "item_uri": kit_uri,
    })
    click.echo(f"Loaded drum rack + kit '{loadable[0].get('name')}' on track {track_index}")


# ── Arrangement commands ─────────────────────────────────────────────

@cli.group()
def arrangement() -> None:
    """Arrangement View operations."""
    pass


@arrangement.command("clear")
@click.pass_context
def arrangement_clear(ctx: click.Context) -> None:
    """Delete all clips from the Arrangement View."""
    conn = _get_conn(ctx)
    result = conn.send_command("clear_arrangement")
    n = result.get("deleted", 0)
    click.echo(f"Arrangement cleared: {n} clip(s) deleted.")


@arrangement.command("play-from")
@click.argument("beat", type=float)
@click.pass_context
def arrangement_play_from(ctx: click.Context, beat: float) -> None:
    """Start Arrangement playback from BEAT position (in beats, 0-based)."""
    conn = _get_conn(ctx)
    conn.send_command("play_from_beat", {"beat": beat})
    click.echo(f"Playback started from beat {beat}")


@arrangement.command("build")
@click.pass_context
def arrangement_build(ctx: click.Context) -> None:
    """Build the Arrangement View from session clips using the house track layout.

    Section layout (128 BPM, A minor house track):
      Intro  : Drums only        (bars 1-8,   beats 0-32)
      +Bass  : Drums + Bass      (bars 9-16,  beats 32-64)
      +Pad   : + Synth Pad       (bars 17-24, beats 64-96)
      Peak   : + Lead            (bars 25-40, beats 96-160)
      Break  : Drums + Pad       (bars 41-48, beats 160-192)
      Outro  : Drums only        (bars 49-56, beats 192-224)
    """
    conn = _get_conn(ctx)

    sections = [
        # Drums: 全区間 (0-224拍)
        {"track_index": 0, "start_beat": 0,   "length": 224, "session_slot": 0},
        # Bass: +Bass〜ピーク (32-160拍)
        {"track_index": 1, "start_beat": 32,  "length": 128, "session_slot": 0},
        # Synth Pad: +Pad〜ブレイク (64-192拍)
        {"track_index": 2, "start_beat": 64,  "length": 128, "session_slot": 0},
        # Lead: ピークのみ (96-160拍)
        {"track_index": 3, "start_beat": 96,  "length": 64,  "session_slot": 0},
    ]

    click.echo("Building arrangement...")
    result = conn.send_command("build_arrangement", {"sections": sections})
    n = result.get("sections_built", 0)
    click.echo(f"Arrangement built: {n} sections placed.")
    click.echo("Switch to Arrangement View in Ableton and press Play.")


# ── Device commands ─────────────────────────────────────────────────

@cli.group()
def device() -> None:
    """Device parameter operations."""
    pass


@device.command("param")
@click.argument("track_index", type=int)
@click.argument("device_index", type=int)
@click.argument("param_name")
@click.argument("value", type=float)
@click.pass_context
def device_param(ctx: click.Context, track_index: int, device_index: int, param_name: str, value: float) -> None:
    """Set a device parameter.

    DEVICE_INDEX: 0-based device position on the track (see 'ableton track info').
    PARAM_NAME: Parameter name, case-insensitive (e.g. 'Filter Freq').
    VALUE: New value (range depends on parameter).

    Example: ableton device param 0 0 "Filter Freq" 800
    """
    conn = _get_conn(ctx)
    result = conn.send_command("set_device_param", {
        "track_index": track_index,
        "device_index": device_index,
        "param_name": param_name,
        "value": value,
    })
    actual_name = result.get("param_name", param_name)
    actual_value = result.get("value", value)
    click.echo(f"Set '{actual_name}' to {actual_value:.3f} on track {track_index}, device {device_index}")


# ── Scene commands ───────────────────────────────────────────────────

@cli.group()
def scene() -> None:
    """Scene operations."""
    pass


@scene.command("fire")
@click.argument("index", type=int)
@click.pass_context
def scene_fire(ctx: click.Context, index: int) -> None:
    """Fire (trigger) a Session View scene by INDEX."""
    conn = _get_conn(ctx)
    conn.send_command("fire_scene", {"scene_index": index})
    click.echo(f"Scene {index} fired")


# ── Entry point ─────────────────────────────────────────────────────

if __name__ == "__main__":
    cli()
