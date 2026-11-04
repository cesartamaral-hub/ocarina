import type { Playable } from './media'

// The YouTube player in the page, driven like an <audio> element so the reader's keys, speed and sentence following work on it.

type Player = {
  playVideo(): void
  pauseVideo(): void
  seekTo(seconds: number, allowSeekAhead: boolean): void
  getCurrentTime(): number
  getDuration(): number
  getPlayerState(): number
  setPlaybackRate(rate: number): void
  getPlaybackRate(): number
  getAvailablePlaybackRates(): number[]
  destroy(): void
}

type YT = {
  Player: new (element: HTMLElement, options: Record<string, unknown>) => Player
}

declare global {
  interface Window {
    YT?: YT
    onYouTubeIframeAPIReady?: () => void
  }
}

let loading: Promise<YT> | null = null

// The player script is loaded once, the first time a video is shown.
export function loadYouTube(): Promise<YT> {
  if (window.YT?.Player) return Promise.resolve(window.YT)
  loading ??= new Promise<YT>((resolve, reject) => {
    const before = window.onYouTubeIframeAPIReady
    window.onYouTubeIframeAPIReady = () => {
      before?.()
      resolve(window.YT as YT)
    }
    const script = document.createElement('script')
    script.src = 'https://www.youtube.com/iframe_api'
    script.onerror = () => {
      loading = null
      reject(new Error('YouTube could not be reached. Check your connection.'))
    }
    document.head.appendChild(script)
  })
  return loading
}

export const ERRORS: Record<number, string> = {
  2: 'That video link is not valid.',
  5: 'The video cannot be played here.',
  100: 'The video was removed or is private.',
  101: "The owner of this video does not allow it to be played inside other apps.",
  150: "The owner of this video does not allow it to be played inside other apps.",
  153: 'YouTube refused to play the video inside the app.',
}

const PLAYING = 1
const nearest = (rates: number[], wanted: number) => rates.reduce((best, r) => (Math.abs(r - wanted) < Math.abs(best - wanted) ? r : best), rates[0] ?? 1)

// The video as something playable. YouTube offers a few speeds (0.25 to 2), so a speed is rounded to the nearest one.
export class YouTubeMedia implements Playable {
  private player: Player

  constructor(player: Player) {
    this.player = player
  }

  get paused() {
    return this.player.getPlayerState() !== PLAYING
  }

  get currentTime() {
    return this.player.getCurrentTime() || 0
  }

  set currentTime(seconds: number) {
    this.player.seekTo(seconds, true)
  }

  get duration() {
    return this.player.getDuration() || NaN
  }

  get playbackRate() {
    return this.player.getPlaybackRate() || 1
  }

  set playbackRate(rate: number) {
    this.player.setPlaybackRate(nearest(this.player.getAvailablePlaybackRates(), rate))
  }

  play() {
    this.player.playVideo()
    return Promise.resolve()
  }

  pause() {
    this.player.pauseVideo()
  }
}
