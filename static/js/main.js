/**
 * static/js/main.js
 * =================
 * Custom JavaScript for the PRJ017 Kiosk CMS admin panel.
 *
 * Responsibilities:
 *   1. Mobile sidebar toggle (hamburger button opens/closes the sidebar)
 *   2. Confirmation dialogs before destructive DELETE actions
 *
 * This file runs after the DOM is fully loaded (DOMContentLoaded event).
 * It does NOT rely on jQuery — plain vanilla JavaScript only.
 */

document.addEventListener('DOMContentLoaded', function () {

    // ----------------------------------------------------------------
    // 1. MOBILE SIDEBAR TOGGLE
    // ----------------------------------------------------------------
    // On small screens (< 992px) the sidebar is hidden off-screen.
    // When the user taps the hamburger icon in the top bar, we add the
    // CSS class 'open' to the sidebar and 'active' to the overlay.
    // The CSS transition in style.css slides the sidebar in smoothly.
    // ----------------------------------------------------------------

    const sidebar       = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const overlay       = document.getElementById('sidebarOverlay');

    /**
     * openSidebar — adds the CSS classes that make the sidebar visible.
     */
    function openSidebar() {
        if (sidebar)  sidebar.classList.add('open');
        if (overlay)  overlay.classList.add('active');
    }

    /**
     * closeSidebar — removes the CSS classes to hide the sidebar again.
     */
    function closeSidebar() {
        if (sidebar)  sidebar.classList.remove('open');
        if (overlay)  overlay.classList.remove('active');
    }

    // Hamburger button click — toggle open/closed
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function () {
            // classList.contains checks whether the class already exists
            if (sidebar && sidebar.classList.contains('open')) {
                closeSidebar();
            } else {
                openSidebar();
            }
        });
    }

    // Tapping the dark overlay closes the sidebar (same as tapping outside)
    if (overlay) {
        overlay.addEventListener('click', closeSidebar);
    }

    // ----------------------------------------------------------------
    // 2. NOTICE DELETE CONFIRMATION DIALOGS
    // ----------------------------------------------------------------
    // When a delete button is clicked, we intercept the form submit event
    // and show a browser confirmation dialog.  If the user clicks Cancel
    // the form submission is prevented and nothing is deleted.
    // This protects against accidental clicks.
    //
    // The form must have class="confirm-delete-form" and the submit button
    // must have data-notice-title="<title>" for the personalised message.
    // ----------------------------------------------------------------

    document.querySelectorAll('.confirm-delete-form').forEach(function (form) {
        form.addEventListener('submit', function (evt) {
            // Find the button inside this specific form that triggered the event
            const btn   = form.querySelector('button[type="submit"]');
            // Read the notice title from the data attribute on the button
            const title = btn ? btn.getAttribute('data-notice-title') : 'this notice';

            // window.confirm() shows a native browser dialog and returns true/false
            const confirmed = window.confirm(
                'Are you sure you want to DELETE "' + title + '"?\n\n' +
                'This will remove the notice from the database AND delete the media file from disk.\n' +
                'This action cannot be undone.'
            );

            if (!confirmed) {
                // Prevent the form from submitting — the user clicked Cancel
                evt.preventDefault();
            }
        });
    });

    // ----------------------------------------------------------------
    // 3. USER DELETE CONFIRMATION DIALOGS
    // ----------------------------------------------------------------
    // Same pattern as above but for the users management page.
    // The button must have data-username="<username>" for the message.
    // ----------------------------------------------------------------

    document.querySelectorAll('.confirm-delete-user-form').forEach(function (form) {
        form.addEventListener('submit', function (evt) {
            const btn      = form.querySelector('button[type="submit"]');
            const username = btn ? btn.getAttribute('data-username') : 'this user';

            const confirmed = window.confirm(
                'Are you sure you want to DELETE the account for "' + username + '"?\n\n' +
                'The user will immediately lose access to the CMS.\n' +
                'This action cannot be undone.'
            );

            if (!confirmed) {
                evt.preventDefault();
            }
        });
    });

}); // end DOMContentLoaded
