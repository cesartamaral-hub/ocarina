import { useEffect, useState } from "react";
import {
  getPref,
  getSystemVoices,
  openVoiceSettings,
  previewSystemVoice,
  setPref,
  type SystemVoices as Row,
} from "./api";
import { notify } from "./notices";
import { SettingRow, SettingsGroup } from "./SettingsKit";

const QUALITY = {
  premium: " · premium",
  enhanced: " · enhanced",
  standard: "",
} as const;

// The voices macOS has installed for each language you study: the Mac system voice says words when nothing else can. Pick one, or leave it on Automatic.
export function SystemVoices() {
  const [rows, setRows] = useState<Row[]>([]);
  const [, setVersion] = useState(0);
  useEffect(() => {
    getSystemVoices().then(setRows, () => undefined);
  }, []);
  async function open() {
    try {
      await openVoiceSettings();
    } catch (e) {
      notify((e as Error).message, 8000);
    }
  }
  async function preview(name: string) {
    try {
      new Audio((await previewSystemVoice(name)).url)
        .play()
        .catch(() => undefined);
    } catch (e) {
      notify((e as Error).message);
    }
  }
  if (rows.length === 0) return null;
  return (
    <SettingsGroup title="Mac system voice">
      {rows.map((r) => {
        const pref = r.code ? getPref<string>(`systemvoice.${r.code}`, "") : "";
        return (
          <SettingRow
            key={r.languageId}
            label={r.language}
            info="The voice built into macOS says words when the AI voice cannot. More voices: System Settings → Accessibility → Spoken Content → System Voice → Manage Voices."
          >
            {r.voices.length === 0 ? (
              <>
                <span className="muted">
                  {r.code
                    ? "No voice installed on this Mac"
                    : "Language not recognised"}
                </span>
                {r.code && (
                  <button className="secondary" onClick={open}>
                    Add a voice…
                  </button>
                )}
              </>
            ) : (
              <>
                <button
                  className="quiet"
                  aria-label={`Preview the ${r.language} voice`}
                  onClick={() =>
                    preview(
                      r.voices.find((v) => v.name === (pref || r.chosen))
                        ?.name ?? r.voices[0].name,
                    )
                  }
                >
                  ▶ Preview
                </button>
                <select
                  aria-label={`Mac system voice for ${r.language}`}
                  value={r.voices.some((v) => v.name === pref) ? pref : ""}
                  onChange={(e) => {
                    setPref(`systemvoice.${r.code}`, e.target.value);
                    setVersion((n) => n + 1);
                  }}
                >
                  <option value="">
                    Automatic ({r.voices[0].name.split(" (")[0]})
                  </option>
                  {r.voices.map((v) => (
                    <option key={v.name} value={v.name}>
                      {v.name.split(" (")[0]}
                      {QUALITY[v.quality]}
                    </option>
                  ))}
                </select>
                <button
                  className="quiet"
                  onClick={open}
                  title="Add more voices in System Settings"
                >
                  More…
                </button>
              </>
            )}
          </SettingRow>
        );
      })}
    </SettingsGroup>
  );
}
