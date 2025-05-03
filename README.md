# Streamlit MLLM Annotation Verification Tool

This Streamlit application provides a web-based user interface for verifying image-caption pairs, potentially aided by votes from Multi-Modal Large Language Models (MLLMs). Users can review images associated with a specific caption, apply filters based on MLLM votes or the number of votes, and assign a human annotation ("True", "False", or "Ambiguous") to each image-caption pair.

## Features

*   **Data Loading:** Loads annotation tasks from a structured JSON file (`annotations_input.json`).
*   **Interactive UI:** Built with Streamlit for easy navigation and interaction.
*   **Caption Selection:** Select a caption from the sidebar to view associated images.
*   **Image Display:** Shows images for the selected caption.
*   **Pagination:** Handles large numbers of images per caption using pagination.
*   **MLLM Information:** Displays which MLLMs (if any) voted for the image-caption pair.
*   **Filtering:**
    *   Filter images based on which MLLMs voted for them (multi-select).
    *   Filter images based on the *number* of MLLMs that voted (multi-select).
*   **Annotation:** Assign "True", "False", or "Ambiguous" labels via radio buttons.
*   **Dynamic Defaults:** For images not yet annotated (`human_annotation` is `null`):
    *   Defaults to "True" if the image has 3 or more MLLM votes.
    *   Defaults to "Ambiguous" if the image has exactly 2 MLLM votes.
    *   Defaults to "False" if the image has 1 or 0 MLLM votes.
*   **State Management:** Uses Streamlit's session state to maintain user selections and current view across interactions.
*   **Saving:** Saves updated human annotations back to the original JSON file.
*   **Error Handling:** Basic checks for file existence and JSON format validity.
*   **Caching:** Uses `@st.cache_data` to speed up data loading.

## Project Structure

```
Streamlit_Annotation/
├── annotation_app.py       # Main Streamlit application script
├── annotations_input.json  # Input data file (needs to be created by user)
├── images/                 # Directory containing image files (needs to be created by user)
├── .gitignore              # Specifies intentionally untracked files by Git
└── README.md               # This file
```

**Note:** The `.gitignore` file currently excludes the `images/` directory. This means image files are not tracked by Git and won't be pushed to a remote repository like GitHub. You will need to manage the `images/` directory and the `annotations_input.json` file separately.

## Setup

1.  **Clone the Repository (if applicable):**
    ```bash
    git clone <your-repository-url>
    cd Streamlit_Annotation
    ```

2.  **Create a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    # Activate the environment
    # Windows:
    .\venv\Scripts\activate
    # macOS/Linux:
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    Create a `requirements.txt` file with the following content:
    ```txt
    streamlit
    Pillow
    ```
    Then install them:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Prepare Data:**
    *   Create the `images/` directory in the project root.
    *   Place your image files inside the `images/` directory (or subdirectories).
    *   Create the `annotations_input.json` file in the project root. Populate it according to the format described below. Make sure the `img_path` values in the JSON correctly point to your image files relative to the project root (e.g., `images/your_image.jpg`).

## Data Format (`annotations_input.json`)

The application expects a JSON file with the following structure:

```json
{
  "Caption Text 1": [
    {
      "img_path": "path/to/image1.jpg", // Relative path from project root
      "votes": ["mllm_name_1", "mllm_name_2"], // List of MLLMs that voted positively (optional)
      "human_annotation": "True" // Can be "True", "False", "Ambiguous", or null (if not yet annotated)
    },
    {
      "img_path": "path/to/image2.png",
      "votes": ["mllm_name_3"],
      "human_annotation": null
    }
    // ... more images for Caption Text 1
  ],
  "Caption Text 2": [
    // ... images for Caption Text 2
  ]
  // ... more captions
}
```

*   The top level is a dictionary where keys are the caption strings.
*   Each caption maps to a list of dictionaries, where each dictionary represents an image associated with that caption.
*   `img_path`: The relative path to the image file.
*   `votes`: (Optional) A list of strings identifying the MLLMs that considered the image relevant to the caption.
*   `human_annotation`: Stores the result of human verification. It should be `null` initially or if not yet annotated. The app will update this field when saved.

## Usage

1.  **Run the App:**
    Open your terminal, navigate to the project directory (`Streamlit_Annotation`), activate your virtual environment, and run:
    ```bash
    streamlit run annotation_app.py
    ```
2.  **Select Caption:** Use the dropdown menu in the sidebar ("1. Select Caption") to choose the caption you want to work on.
3.  **Filter Images (Optional):**
    *   Use the "2. Filter by MLLM Votes" multi-select to show only images voted by specific MLLMs.
    *   Use the "3. Filter by Number of Votes" multi-select to show only images with a certain number of MLLM votes.
4.  **Annotate:** For each image displayed on the page:
    *   Review the image and the caption (shown at the top).
    *   See the MLLM votes listed below the image.
    *   Select "True", "False", or "Ambiguous" using the radio buttons.
5.  **Navigate Pages:** Use the "Previous" and "Next" buttons below the image list if there are multiple pages for the current caption/filter combination.
6.  **Save:** Click the "💾 Update & Save Annotations" button in the sidebar to save the annotations you made *on the currently viewed page* back to the `annotations_input.json` file.

## Code Structure (`annotation_app.py`)

*   **Imports & Configuration:** Basic setup, library imports, and configuration constants (`JSON_FILE_PATH`, `IMAGES_PER_PAGE`, etc.).
*   **Helper Functions:**
    *   `load_data()`: Loads and preprocesses data from JSON, handles initialization of `human_annotation`, cached for performance.
    *   `get_all_mllm_voters()`: Extracts unique MLLM names from the data, cached.
    *   `save_data()`: Saves the updated data structure back to the JSON file.
*   **Session State Initialization:** Ensures necessary variables (`annotation_data`, `selected_caption`, `current_page`, filters) persist across user interactions.
*   **Main App Logic:** Sets the page title. Checks if data loaded successfully.
*   **Sidebar:** Contains widgets for selecting captions and applying filters. Logic updates session state and triggers reruns when selections change.
*   **Annotation Area:**
    *   Displays the selected caption.
    *   Applies MLLM name and vote count filters to the image list.
    *   See the MLLM votes listed below the image. Note the default selection based on vote count if the image hasn't been annotated before.
    *   Iterates through the images for the current page, displaying the image, path, votes, and the radio button annotation widget.
    *   Collects annotations made on the current page into `current_annotations`.
*   **Save Button Logic:** When clicked, iterates through `current_annotations`, finds the corresponding image in the main data structure (using `img_path` for robustness), updates its `human_annotation` if changed, and calls `save_data()`.
*   **Debugging Output (Optional):** A checkbox in the sidebar can display the raw JSON data for the selected caption.

## Customization

*   **Data Source:** Modify `load_data()` and `save_data()` if your annotations are stored differently (e.g., CSV, database).
*   **Annotation Options:** Change the `ANNOTATION_OPTIONS` list. Modify the dynamic default logic in the annotation area if needed.
*   **Layout:** Adjust Streamlit columns (`st.columns`), image widths (`st.image(width=...)`), and other UI elements.
*   **Filtering:** Add more complex filtering logic based on other image metadata if available in your JSON.
*   **Image Loading:** Enhance error handling or add support for images loaded from URLs.