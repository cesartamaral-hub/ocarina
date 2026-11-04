// What the reader needs of a player: an <audio> element has all of it, and so does the YouTube player (see youtube.ts).
export type Playable = Pick<HTMLAudioElement, 'paused' | 'currentTime' | 'duration' | 'playbackRate' | 'play' | 'pause'>
