# Developer README: Streamlit MLLM Annotation Verification Tool

This document provides a technical deep dive into the `annotation_app.py` script, intended for developers looking to understand, maintain, or extend the application.

## 1. Project Overview

This Streamlit application facilitates the human verification of image-caption pairs. It allows users to load annotation tasks from user-specific JSON files, view images associated with captions, apply filters, and record their judgment ("True", "False", "Ambiguous"). The application uses a grid layout for efficient display and implements dynamic default annotations based on pre-existing MLLM votes.

## 2. Core Features

*   **User-Specific Data:** Loads/saves annotations from/to separate JSON files per user (e.g., `annotations/annotations_alice.json`).
*   **Interactive UI:** Built with Streamlit, featuring sidebar navigation and filtering.
*   **Grid Layout:** Displays images and annotation options in a configurable grid (e.g., 3 columns).
*   **Filtering:** Supports multi-select filtering based on MLLM voters and the *number* of votes.
*   **Dynamic Defaults:** Pre-selects annotation radio buttons based on MLLM vote count for unannotated items.
*   **Pagination:** Handles navigation through large sets of images per caption.
*   **State Management:** Leverages `st.session_state` to maintain UI state across interactions.
*   **Caching:** Uses `st.cache_data` for efficient data loading.

## 3. Setup & Dependencies

*   **Python:** 3.8+ recommended.
*   **Dependencies:** `streamlit`, `Pillow`. Install using `pip install -r requirements.txt` (create this file if needed).
*   **Directory Structure:**
    ```
    Streamlit_Annotation/
    ├── annotation_app.py       # Main application script
    ├── annotations/             # Directory for user JSON files
    │   ├── annotations_user1.json
    │   └── ...
    ├── images/                 # Directory containing image files
    └── README_DEV.md           # This file
    ```
*   **Permissions:** Ensure the process running Streamlit has read/write access to the `annotations/` directory and read access to the `images/` directory.

## 4. Data Format (`annotations/<user>.json`)

Each user's JSON file follows this structure:

```json
{
  "Caption Text 1": [
    {
      "img_path": "images/subdir/image1.jpg", // Relative path from project root
      "votes": ["mllm_A", "mllm_B", "mllm_C"], // Optional: List of MLLMs that voted positively
      "human_annotation": "True" // "True", "False", "Ambiguous", or null
    },
    {
      "img_path": "images/image2.png",
      "votes": ["mllm_A"],
      "human_annotation": null // Not yet annotated by this user
    }
    // ... more images for this caption
  ],
  "Another Caption": [
    // ...
  ]
}
```

*   **Keys:** Top-level keys are the caption strings.
*   **Values:** Each caption maps to a list of image information dictionaries.
*   **`img_path`:** Crucial field, relative path to the image file from the project root. Used for display and uniquely identifying images during saving.
*   **`votes`:** Optional list of strings identifying MLLMs. Used for filtering and dynamic defaults.
*   **`human_annotation`:** Stores the user's annotation. `null` signifies it hasn't been annotated yet.

## 5. Code Deep Dive (`annotation_app.py`)

### 5.1. Configuration Constants

*   `ANNOTATIONS_DIR`: Specifies the subdirectory containing user JSON files.
*   `IMAGES_PER_PAGE`: Controls pagination.
*   `ANNOTATION_OPTIONS`: Defines the available annotation choices.
*   `IMAGES_PER_ROW`: Defines the number of columns in the image grid display.

### 5.2. Helper Functions

*   **`load_data(json_path)`:**
    *   Decorated with `@st.cache_data` to memoize results based on `json_path`. Avoids reloading the same file repeatedly during a session unless the file content changes (Streamlit handles cache invalidation).
    *   Opens and parses the specified JSON file.
    *   **Crucially, iterates through the loaded data and uses `img_info.setdefault("human_annotation", None)` to ensure every image dictionary has the `human_annotation` key, preventing `KeyError` later.**
    *   Handles `FileNotFoundError` (returns `None`), `json.JSONDecodeError` (shows `st.error`, returns `None`), and other exceptions.
*   **`get_all_mllm_voters(data)`:**
    *   Decorated with `@st.cache_data`. Assumes the input `data` structure is relatively stable within a session for a given loaded file.
    *   Iterates through all images across all captions in the provided `data` dictionary.
    *   Uses a `set` to efficiently collect unique voter names from the `votes` list (using `img_info.get("votes", [])` for safety).
    *   Returns a sorted list of unique voter names.
*   **`save_data(json_path, data)`:**
    *   Opens the specified `json_path` in write mode (`'w'`), **which truncates the file first**.
    *   Uses `json.dump()` to write the provided `data` structure (typically the modified `st.session_state.annotation_data`) back to the file with indentation for readability.
    *   Includes basic error handling for the write operation.

### 5.3. Session State Management (`st.session_state`)

Streamlit reruns the script on almost every interaction. `st.session_state` is used to persist state across these reruns.

*   `annotation_data`: Holds the entire data structure loaded from the user's JSON file. Initialized to `None`.
*   `selected_annotation_file`: Stores the *full path* to the currently selected user JSON file. Initialized to `None`.
*   `selected_caption`: Stores the currently selected caption string. Initialized to `None`.
*   `current_page`: Tracks the current page number for pagination. Initialized to `1`.
*   `selected_mllms`: List storing the MLLMs selected in the filter. Initialized to `[]`.
*   `selected_vote_counts`: List storing the vote counts selected in the filter. Initialized to `[]`.

### 5.4. Main Application Flow & Sidebar Logic

1.  **Title:** Sets the application title.
2.  **File Selection (Sidebar):**
    *   Lists `.json` files found in `ANNOTATIONS_DIR`.
    *   Uses `st.selectbox` to allow the user to choose a file.
    *   **State Update:** If a new, valid file is selected:
        *   Updates `st.session_state.selected_annotation_file`.
        *   Calls `load_data()` to load the content into `st.session_state.annotation_data`.
        *   Resets `selected_caption`, `current_page`, and filter states.
        *   Calls `st.rerun()` to immediately refresh the app with the new data context.
    *   If the selection returns to the placeholder, clears the loaded data and file path, then reruns.
3.  **Data Load Check:** If `st.session_state.annotation_data` is `None` (no file selected/loaded), displays a warning and stops execution using `st.stop()`.
4.  **Caption Selection (Sidebar):**
    *   Populates `st.selectbox` with captions from the loaded `annotation_data`.
    *   **State Update:** If a new caption is selected:
        *   Updates `st.session_state.selected_caption`.
        *   Resets `current_page` and `selected_vote_counts`.
        *   Calls `st.rerun()` to update the main annotation area.
5.  **Filters (Sidebar):**
    *   MLLM Filter: Uses `st.multiselect` populated by `get_all_mllm_voters()`. Updates `st.session_state.selected_mllms` and reruns if changed.
    *   Vote Count Filter: Dynamically calculates available vote counts for the *selected caption*. Uses `st.multiselect`. Updates `st.session_state.selected_vote_counts` and reruns if changed.

### 5.5. Annotation Area Logic

This section only runs if a caption is selected (`if st.session_state.selected_caption:`).

1.  **Filtering:**
    *   Retrieves the full image list for the caption: `all_images_for_caption`.
    *   Applies the MLLM filter (`st.session_state.selected_mllms`) using `any()` for multi-select logic.
    *   Applies the vote count filter (`st.session_state.selected_vote_counts`) to the result of the MLLM filter.
    *   The final list is stored in `filtered_images`.
2.  **Pagination:**
    *   Calculates `total_images` and `total_pages` based on `filtered_images`.
    *   Displays "Previous" / "Next" buttons and the current page info. Button clicks update `st.session_state.current_page` and trigger `st.rerun()`.
    *   Calculates `start_idx` and `end_idx` for slicing `filtered_images` to get `images_to_display` for the current page.
3.  **Grid Display:**
    *   Iterates through `images_to_display` in steps of `IMAGES_PER_ROW`.
    *   Uses `st.columns(IMAGES_PER_ROW)` to create columns for each row.
    *   An inner loop places each image and its widgets into the corresponding column (`with cols[j]:`).
4.  **Image Cell Content (within `with cols[j]:`)**
    *   Retrieves `img_path`, `votes`, `current_annotation`.
    *   **Dynamic Default:** If `current_annotation` is `None`, calculates the default ("True", "False", "Ambiguous") based on `len(votes)`. Otherwise, uses the existing `current_annotation`.
    *   Calculates `default_index` for `st.radio`.
    *   Displays the image using `st.image(width=...)` for consistent sizing. Handles image loading errors.
    *   Displays image path (basename only) and votes.
    *   Displays `st.radio` for annotation. **Crucially, uses a unique `key`** (combining caption, path, index) to ensure Streamlit correctly manages the state of each radio button group. `horizontal=True` saves space.
    *   Stores the selected choice from `st.radio` into the `current_annotations` dictionary, keyed by the `page_relative_index`.

### 5.6. Save Logic

Triggered by the "Update & Save Annotations" button in the sidebar.

1.  Initializes `updated_count = 0`.
2.  Iterates through the `current_annotations` dictionary (which only contains annotations made *on the currently displayed page*).
3.  For each `page_relative_index` and `annotation_value`:
    *   Retrieves the corresponding `img_info_displayed` from the `images_to_display` list.
    *   Gets the `img_path_to_update`.
    *   **Robust Update:** Iterates through the *original* list of images for the caption in `st.session_state.annotation_data[caption]`.
    *   Finds the dictionary in the original list where `original_img_info.get("img_path") == img_path_to_update`. This is essential because filtering and pagination change the indices.
    *   Compares the `annotation_value` with the existing `human_annotation` in the found `original_img_info`.
    *   If they differ, updates `original_img_info["human_annotation"] = annotation_value` and increments `updated_count`.
4.  If `updated_count > 0`, calls `save_data()` with the `selected_annotation_file` path and the modified `st.session_state.annotation_data`.
5.  Displays status messages (`st.sidebar.info`, `st.sidebar.warning`).

## 6. Potential Improvements / Future Work

*   **Error Handling:** More specific error handling during image loading or file operations.
*   **Performance:** For extremely large JSON files or image sets, consider database backends or more optimized data loading/filtering.
*   **UI/UX:** Add progress indicators for saving, confirmation dialogs, keyboard shortcuts.
*   **Conflict Resolution (if sharing files):** Implement strategies if multiple users might edit the *same* file (though the current design avoids this).
*   **Annotation Schema:** Allow configuration of annotation options or add more complex annotation types (e.g., bounding boxes - requires significant changes).
*   **Testing:** Add unit or integration tests.

## 7. Contributing

*   Follow existing code style.
*   Ensure changes are well-documented.
*   Test thoroughly before submitting pull requests.
*   Update this README if significant architectural changes are made.

```