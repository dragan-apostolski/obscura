/** Tiny window-event bus so any component (header, product page) can open the
 *  chat dock and optionally pre-fill a question, without global state. */

export const CHAT_EVENT = "obscura:chat";

export type ChatEventDetail = { prompt?: string };

export function openChat(prompt?: string) {
  window.dispatchEvent(new CustomEvent<ChatEventDetail>(CHAT_EVENT, { detail: { prompt } }));
}
