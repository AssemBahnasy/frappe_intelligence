/**
 * ui.js
 * -----
 * Panel state machine, draggable FAB, progress/bubble helpers.
 */

export const uiMethods = {
    _makeFabDraggable() {
        const self = this;
        const root = document.getElementById("fi-widget-root");
        const fab = document.getElementById("fi-fab");
        const DRAG_THRESHOLD = 5;
        let dragging = false;
        let startX, startY, startLeft, startTop;

        try {
            const saved = JSON.parse(localStorage.getItem("fi_widget_pos") || "null");
            if (saved && typeof saved.left === "number" && typeof saved.top === "number") {
                root.style.bottom = "auto";
                root.style.left = Math.max(0, Math.min(window.innerWidth - 56, saved.left)) + "px";
                root.style.top = Math.max(0, Math.min(window.innerHeight - 56, saved.top)) + "px";
                self._updateSideClass(parseInt(root.style.left));
            } else {
                requestAnimationFrame(() => {
                    const rect = root.getBoundingClientRect();
                    self._updateSideClass(rect.left);
                });
            }
        } catch (_) {
            requestAnimationFrame(() => {
                const rect = root.getBoundingClientRect();
                self._updateSideClass(rect.left);
            });
        }

        function onStart(cx, cy) {
            const rect = root.getBoundingClientRect();
            startX = cx; startY = cy;
            startLeft = rect.left; startTop = rect.top;
            dragging = true;
            self._dragMoved = false;
            root.style.bottom = "auto";
            root.style.right = "auto";
            root.style.left = startLeft + "px";
            root.style.top = startTop + "px";
            fab.style.cursor = "grabbing";
            fab.style.transition = "none";
        }

        function onMove(cx, cy) {
            if (!dragging) return;
            const dx = cx - startX;
            const dy = cy - startY;
            if (!self._dragMoved && (Math.abs(dx) > DRAG_THRESHOLD || Math.abs(dy) > DRAG_THRESHOLD)) {
                self._dragMoved = true;
            }
            if (!self._dragMoved) return;
            const newLeft = Math.max(0, Math.min(window.innerWidth - 56, startLeft + dx));
            const newTop = Math.max(0, Math.min(window.innerHeight - 56, startTop + dy));
            root.style.left = newLeft + "px";
            root.style.top = newTop + "px";
            self._updateSideClass(newLeft);
        }

        function onEnd() {
            if (!dragging) return;
            dragging = false;
            fab.style.cursor = "grab";
            fab.style.transition = "";
            if (self._dragMoved) {
                try {
                    localStorage.setItem("fi_widget_pos", JSON.stringify({
                        left: parseInt(root.style.left),
                        top: parseInt(root.style.top),
                    }));
                } catch (_) { }
            }
        }

        fab.addEventListener("mousedown", (e) => { onStart(e.clientX, e.clientY); e.preventDefault(); });
        document.addEventListener("mousemove", (e) => onMove(e.clientX, e.clientY));
        document.addEventListener("mouseup", onEnd);

        fab.addEventListener("touchstart", (e) => {
            onStart(e.touches[0].clientX, e.touches[0].clientY);
            e.preventDefault();
        }, { passive: false });
        document.addEventListener("touchmove", (e) => {
            if (!dragging) return;
            onMove(e.touches[0].clientX, e.touches[0].clientY);
            e.preventDefault();
        }, { passive: false });
        document.addEventListener("touchend", onEnd);
    },

    _updateSideClass(leftPx) {
        const root = document.getElementById("fi-widget-root");
        if (!root) return;
        root.classList.toggle("fi-right-side", leftPx > window.innerWidth / 2);
    },

    _openPanel(id) {
        $(".fi-panel").removeClass("fi-visible").addClass("fi-hidden");
        $(`#${id}`).removeClass("fi-hidden").addClass("fi-visible");
        this._state = id;
        if (id === "fi-chat-panel") {
            this._mountChatIsland();
            const iconEl = document.querySelector("#fi-fab .fi-fab-icon");
            if (iconEl) iconEl.textContent = "✕";
        }
    },

    _closeAll(resetFab = true) {
        this._unmountChatIsland();
        $(".fi-panel").removeClass("fi-visible").addClass("fi-hidden");
        $("#fi-progress").addClass("fi-hidden");
        $(".fi-result-footer").show();
        this._pendingReview = null;
        if (resetFab) {
            const iconEl = document.querySelector("#fi-fab .fi-fab-icon");
            if (iconEl) iconEl.innerHTML = this._fabDefaultIcon;
            this._state = "idle";
        }
    },

    _showProgress(msg) {
        $("#fi-progress-text").text(msg || __("Processing…"));
        $("#fi-progress").removeClass("fi-hidden");
    },

    _setProgress(msg) {
        $("#fi-progress-text").text(msg);
    },

    _hideProgress() {
        $("#fi-progress").addClass("fi-hidden");
    },

    _showBubble(text) {
        $("#fi-bubble-text").text(text);
        $("#fi-bubble").removeClass("fi-hidden").addClass("fi-visible");
    },

    _hideBubble() {
        $("#fi-bubble").removeClass("fi-visible").addClass("fi-hidden");
    },

    _mountChatIsland() {
        // Delegate to chat_island.js lifecycle manager (imported in app.bundle.js)
        if (typeof window.__fi_mountChatIsland === "function") {
            window.__fi_mountChatIsland(this);
        }
    },

    _unmountChatIsland() {
        if (typeof window.__fi_unmountChatIsland === "function") {
            window.__fi_unmountChatIsland();
        }
    },
};
