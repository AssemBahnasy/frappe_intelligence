/**
 * dom.js
 * ------
 * DOM construction and inline styles for the Intelligence Concierge widget.
 */

export const domMethods = {
  _buildDOM() {
    $("#fi-widget-root").remove();

    const root = $(`
      <div id="fi-widget-root" dir="${document.documentElement.dir || 'ltr'}">

        <!-- Notification bubble -->
        <div id="fi-bubble" class="fi-notif fi-hidden">
          <span id="fi-bubble-text"></span>
          <button id="fi-bubble-close" class="fi-notif-close" aria-label="Close">✕</button>
        </div>

        <!-- FAB -->
        <button id="fi-fab" class="fi-fab" aria-label="${__("Intelligence Concierge")}" title="${__("Intelligence Concierge")}">
          <span class="fi-fab-icon">${this._fabDefaultIcon}</span>
        </button>

        <!-- Chat panel (Vue island) — Vue mounts into #fi-panel-body -->
        <div id="fi-chat-panel" class="fi-panel fi-hidden">
          <div id="fi-panel-body"></div>
        </div>

      </div>
    `);

    $("body").append(root);
    this._injectStyles();
  },

  _injectStyles() {
    if ($("#fi-widget-styles").length) return;
    $("head").append(`<style id="fi-widget-styles">
      /* ---- Layout & positioning ---- */
      #fi-widget-root {
        position: fixed;
        bottom: 24px;
        inset-inline-start: 24px;
        z-index: 9999;
        font-family: inherit;
      }

      /* ---- FAB ---- */
      .fi-fab {
        width: 56px; height: 56px;
        border-radius: 50%;
        background: var(--primary, #2c9af1);
        color: #fff;
        border: none;
        font-size: 22px;
        cursor: grab;
        box-shadow: 0 4px 14px rgba(0,0,0,0.25);
        transition: transform 0.2s, filter 0.2s;
        display: flex; align-items: center; justify-content: center;
        user-select: none; -webkit-user-select: none;
      }
      .fi-fab:hover { filter: brightness(0.9); transform: scale(1.07); }
      .fi-fab:active { cursor: grabbing; transform: scale(1.0); }
      .fi-fab-custom-icon { width: 28px; height: 28px; border-radius: 50%; object-fit: cover; }

      /* ---- Notification bubble ---- */
      .fi-notif {
        position: absolute;
        bottom: 68px; left: 0;
        background: var(--card-bg, #fff);
        color: var(--text-color, #1a1a1a);
        border: 1px solid var(--border-color, #e4e4e7);
        border-radius: 8px;
        padding: 8px 12px;
        max-width: 280px;
        font-size: 12px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.12);
        display: flex; align-items: flex-start; gap: 6px;
        cursor: pointer;
      }
      .fi-notif-close {
        background: none; border: none; cursor: pointer;
        color: var(--text-muted, #6c757d); font-size: 11px; padding: 0; margin-inline-start: auto;
      }

      /* ---- Panel side-flip ---- */
      #fi-widget-root.fi-right-side .fi-panel { left: auto; right: 0; }
      #fi-widget-root.fi-right-side .fi-notif { left: auto; right: 0; }

      /* ---- Panels ---- */
      .fi-panel {
        position: absolute;
        bottom: 68px; left: 0;
        width: 360px;
        background: var(--card-bg, #fff);
        border-radius: 12px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.15);
        overflow: hidden;
        animation: fi-slide-up 0.2s ease;
      }
      .fi-hidden { display: none !important; }
      .fi-visible { display: flex !important; flex-direction: column; }

      @keyframes fi-slide-up {
        from { opacity: 0; transform: translateY(12px); }
        to   { opacity: 1; transform: translateY(0); }
      }

      /* ---- Chat panel (Vue island) ---- */
      #fi-chat-panel { height: 500px; }
      #fi-panel-body { display: flex; flex-direction: column; flex: 1; min-height: 0; }
    </style>`);
  },
};
