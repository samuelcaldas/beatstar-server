# Android tutorial runtime observations

**Run date:** 2026-10-10<br>
**Client:** Beatstar 36.1.4.9545, Unity 2022.3.50f1<br>
**Target:** Android emulator `emulator-5554`, 1080×2400<br>
**Status:** **INCONCLUSIVE — no verified gameplay completion**

This record captures a live investigation of the first-song tutorial against the local private server. It does not claim that the selected song played to completion, that a score was earned, or that a gameplay audit was accepted.

## Verified input and UI observations

- The client was at the tutorial screen showing **“TAP TO START”** and **“Use Both Thumbs.”**
- Early console-generated contacts had zero touch pressure. Android classified those pointers as **hovering**, not touching; a regular single tap and those contacts did not advance the screen.
- Adding `ABS_MT_PRESSURE` and nonzero `ABS_MT_TOUCH_MAJOR` produced two simultaneous `FINGER` entries under `TouchStatesByDisplay` for the foreground Unity activity. This verifies that the input reached Android as two real touch pointers; it does not by itself prove that a game interaction was scored.
- After a held two-thumb contact and release, the UI changed from the start prompt to a brighter view with a centered **“PERFECT”** zone. A subsequent eight-frame capture and further taps showed no visible chart or result progression.
- Evidence captures are local, ignored artifacts in `.playwright-mcp/`: `current_screen.png`, `tutorial-pressure-contact.png`, `tutorial-after-pressure-release.png`, `tutorial-after-two-thumb-tap.png`, and `tutorial-sequence-00.png` through `tutorial-sequence-07.png`.

## Cached client asset observations

The app's external `UnityCache` contained Unity bundles whose printable internal paths included:

- `s/beatmapinteractions/660.byt`, with the chart label `710-1`.
- `s/audio/banks/tst00687.byt`.
- `s/audio/banks/tst00942.byt` in a second cached bundle.

The first chart/audio identifiers are consistent with the **candidate** Sweet Home Alabama tutorial package documented in `music_asset_contract.md`. Cache presence and matching names do not prove that the client selected, successfully loaded, or played that song's bank/chart. The cache was inspected read-only; no asset contents were modified.

## IL2CPP state-transition evidence

The `dump.cs` declarations and method-body inspection establish this controller sequence:

1. `EndIntroAndStartGamePlay` sets `GameController.StateType.WaitingForStart` (`3`); it does not directly enter `Playing`.
2. `MusicPlayerStateChangedDuringWaitingForState` enters `Playing` (`4`) only if the controller is still waiting and the callback reports `MusicPlayer.eMusicState.Game` (`1`).
3. `TickWaitingForStart` updates intro interaction visuals; it is not the state transition.
4. `RhythmGameIntroHUD.OnPlayButtonClicked` dispatches a HUD event. Its runtime subscriber was not resolved, so the button-to-music-start path remains unverified.

Thus visible touch input alone is insufficient evidence of gameplay. The decisive missing observation is a successful selected-music playback/state notification followed by a changing chart and a genuine result/audit.

## Server-side content observations

- The container initially had no `/app/data/configs` directory. I copied `SongConfig.bin`, `BeatmapsConfig.bin`, and `AssetsConfig.bin` into the mounted, ignored `./data/configs/` directory without overwriting existing files. Their SHA-256 hashes match the source files in the other local checkout, and the running container now sees all three files.
- `CMSHandler` advertises these binaries when present; it omits the three music configs when they are absent (`server/handlers/cms_handler.py:41` and `server/assets/catalog.py:7`). This provisioning happened after the captured tutorial state, so those captures do not prove the client re-fetched or used the binaries.
- `SongsHandler` still returns only two synthetic catalog entries (`starter_song_01` and `starter_song_02`), not the four observed FTUE starter songs (`server/handlers/songs_handler.py:14`).
- These are server-side content limitations, but there is no captured request/response correlation proving which response caused the current client state.

## Audio, server, and completion evidence limits

- AudioFlinger showed a Beatstar-owned audio track as active and its output thread was not in standby during a later sample. This is evidence of an active app audio track, **not** proof that the selected song bank was playing or that audible song content changed.
- Recent filtered client logs showed ping and analytics-proxy RPC summaries, but no gameplay audit was observed. The server container's HTTP access log showed health checks only; that log does not expose the TCP Protobuf request path and cannot establish that no TCP requests occurred.
- No result screen, `RhythmGameEnded` audit, or before/after profile persistence check was observed. Health checks, synthetic score tooling, prior stars, and this UI transition are not accepted as completion proof.

## Remaining gate

Keep the native playback and tutorial-completion status blocked until the HUD event subscriber and music load/play callback are confirmed, chart progression is visible under real multitouch, and a genuine result screen plus corresponding server-side audit/profile change are captured for a clean player profile. See `music_asset_contract.md` for the broader asset/export requirements.
