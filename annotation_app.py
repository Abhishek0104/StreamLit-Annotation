import streamlit as st
import json
import os
from PIL import Image
import math

# --- Page Config (MUST be the first Streamlit command) ---
st.set_page_config(layout="wide") # Use wide layout for more space

# --- Configuration ---
ANNOTATIONS_DIR = 'annotations' # Directory where user annotation files are stored
IMAGES_PER_PAGE = 10  # Number of images to display per page
ANNOTATION_OPTIONS = ["True", "False", "Ambiguous"]
IMAGES_PER_ROW = 3 # Number of images to display side-by-side
# DEFAULT_ANNOTATION constant is removed as it's now dynamic


# --- Helper Functions ---

@st.cache_data # Cache the data loading to avoid reloading on every interaction
def load_data(json_path):
    """Loads the annotation data from the specified JSON file.
    Returns an empty dictionary if the file doesn't exist (shouldn't happen if selected).
    """
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        # Initialize human_annotation if it doesn't exist
        for caption, images in data.items():
            for img_info in images:
                # Ensure the key exists, default to None if missing within the file
                img_info.setdefault("human_annotation", None)
        return data
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        st.error(f"Error: Could not decode JSON from {json_path}. Check its format.")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred during data loading: {e}")
        return None

@st.cache_data
def get_all_mllm_voters(data):
    """Extracts all unique MLLM voter names from the dataset."""
    voters = set()
    if data:
        for caption, images in data.items():
            for img_info in images:
                voters.update(img_info.get("votes", []))
    return sorted(list(voters))

def save_data(json_path, data):
    """Saves the updated annotation data back to the specified JSON file."""
    try:
        with open(json_path, 'w') as f:
            # Save the provided data structure directly
            json.dump(data, f, indent=2) # Use the 'data' argument passed to the function
        st.success(f"Annotations successfully saved to {json_path}!")
    except Exception as e:
        st.error(f"Error saving data to {json_path}: {e}")

# --- Initialize Session State ---
if 'annotation_data' not in st.session_state:
    st.session_state.annotation_data = None # Will be loaded based on file selection

if 'selected_annotation_file' not in st.session_state:
    st.session_state.selected_annotation_file = None

if 'selected_caption' not in st.session_state:
    st.session_state.selected_caption = None

if 'current_page' not in st.session_state:
    st.session_state.current_page = 1

if 'selected_mllms' not in st.session_state:
    st.session_state.selected_mllms = [] # Initialize empty list for MLLM filter

if 'selected_vote_counts' not in st.session_state:
    st.session_state.selected_vote_counts = [] # Initialize empty list for vote count filter
    
if 'score_sort_order' not in st.session_state:
    st.session_state.score_sort_order = "None" # Options: "None", "Ascending", "Descending"


# --- Main App Logic ---
# st.set_page_config(layout="wide") # Use wide layout for more space
st.title("MLLM Annotation Verification Tool")

# --- Annotation File Selection ---
st.sidebar.subheader("0. Select Annotation File")

available_files = []
if os.path.isdir(ANNOTATIONS_DIR):
    try:
        # List files in the annotations directory
        files = [f for f in os.listdir(ANNOTATIONS_DIR) if f.endswith('.json') and os.path.isfile(os.path.join(ANNOTATIONS_DIR, f))]
        available_files = [os.path.join(ANNOTATIONS_DIR, f) for f in files] # Store full paths
    except OSError as e:
        st.sidebar.error(f"Error reading directory {ANNOTATIONS_DIR}: {e}")
else:
    st.sidebar.warning(f"Annotations directory '{ANNOTATIONS_DIR}' not found. Please create it.")

# Add a placeholder option
display_options = ["-- Select a file --"] + available_files

selected_file_sidebar = st.sidebar.selectbox(
    "Choose your annotation file:",
    options=display_options,
    index=0, # Default to placeholder
    key="file_selector"
)

# Load data if a valid file is selected and it's different from the current one
if selected_file_sidebar != "-- Select a file --" and selected_file_sidebar != st.session_state.selected_annotation_file:
    st.session_state.selected_annotation_file = selected_file_sidebar
    st.session_state.annotation_data = load_data(st.session_state.selected_annotation_file)
    # Reset other states when file changes
    st.session_state.selected_caption = None
    st.session_state.current_page = 1
    st.session_state.selected_mllms = []
    st.session_state.selected_vote_counts = []
    st.session_state.score_sort_order = "None" # Reset score sort order
    st.rerun()
elif selected_file_sidebar == "-- Select a file --" and st.session_state.selected_annotation_file is not None:
    # Clear data if selection goes back to placeholder
    st.session_state.selected_annotation_file = None
    st.session_state.annotation_data = None
    st.session_state.selected_caption = None
    st.rerun()

# Ensure data is loaded
if st.session_state.annotation_data is None:
    st.warning("Please select your annotation file from the sidebar to begin.")
    st.stop() # Stop execution if no file is loaded

# --- Sidebar for Caption Selection ---
# st.sidebar.header("Select Caption")
st.sidebar.header("Navigation & Filters")
available_captions = list(st.session_state.annotation_data.keys())
all_mllms = get_all_mllm_voters(st.session_state.annotation_data) # Get all unique MLLM names

# --- Caption Selector ---
st.sidebar.subheader("1. Select Caption")

# Use a selectbox for captions
selected_caption_sidebar = st.sidebar.selectbox(
    "Choose a caption to annotate:",
    options=[""] + available_captions, # Add empty option
    index=0, # Default to empty
    key="caption_selector" # Assign a key
)

# Update session state if selection changes and reset page
if selected_caption_sidebar and selected_caption_sidebar != st.session_state.selected_caption:
    st.session_state.selected_caption = selected_caption_sidebar
    st.session_state.current_page = 1 # Reset page when caption changes
    st.session_state.selected_vote_counts = [] # Reset vote count filter when caption changes
    # Clear previous annotation widgets' states implicitly by changing the main view
    st.rerun() # Rerun to update the main view immediately

# --- MLLM Filter ---
st.sidebar.subheader("2. Filter by MLLM Votes")
selected_mllms_sidebar = st.sidebar.multiselect(
    "Show images voted by (leave empty to show all):",
    options=all_mllms,
    default=st.session_state.selected_mllms, # Use session state for persistence
    key="mllm_filter_selector"
)

# Update session state if MLLM filter changes and reset page
if selected_mllms_sidebar != st.session_state.selected_mllms:
    st.session_state.selected_mllms = selected_mllms_sidebar
    st.session_state.current_page = 1 # Reset page when filter changes
    st.rerun() # Rerun to update the view

# --- Vote Count Filter (Conditional on Caption Selection) ---
available_vote_counts = []
if st.session_state.selected_caption:
    all_images_for_caption_unfiltered = st.session_state.annotation_data[st.session_state.selected_caption]
    vote_counts = {len(img.get("votes", [])) for img in all_images_for_caption_unfiltered if img.get("votes")}
    available_vote_counts = sorted(list(vote_counts))

st.sidebar.subheader("3. Filter by Number of Votes")
if available_vote_counts:
    selected_counts_sidebar = st.sidebar.multiselect(
        "Show images with this many votes:",
        options=available_vote_counts,
        default=st.session_state.selected_vote_counts,
        key="vote_count_filter_selector"
    )
    # Update session state if vote count filter changes and reset page
    if selected_counts_sidebar != st.session_state.selected_vote_counts:
        st.session_state.selected_vote_counts = selected_counts_sidebar
        st.session_state.current_page = 1 # Reset page when filter changes
        st.rerun() # Rerun to update the view
else:
    st.sidebar.write("Select a caption to see vote count filter options.")
    # Ensure filter is cleared if no options are available
    st.session_state.selected_vote_counts = []


# --- Score Sort Filter ---
st.sidebar.subheader("4. Sort by Score")
score_sort_options = ["None", "Ascending", "Descending"]

# Determine the current index for the selectbox
try:
    current_score_sort_index = score_sort_options.index(st.session_state.score_sort_order)
except ValueError:
    current_score_sort_index = 0 # Default to "None" if state is somehow invalid

selected_score_sort_order_sidebar = st.sidebar.selectbox(
    "Sort images by score:",
    options=score_sort_options,
    index=current_score_sort_index,
    key="score_sort_selector"
)
if selected_score_sort_order_sidebar != st.session_state.score_sort_order:
    st.session_state.score_sort_order = selected_score_sort_order_sidebar
    st.session_state.current_page = 1 # Reset page when sort order changes
    st.rerun()


# --- Annotation Area ---
if st.session_state.selected_caption:
    caption = st.session_state.selected_caption
    st.header(f"Annotating for Caption:")
    st.subheader(f"`{caption}`")

    # --- Apply Filters ---
    all_images_for_caption = st.session_state.annotation_data[caption]
    mllm_filter = st.session_state.selected_mllms

    vote_count_filter = st.session_state.selected_vote_counts

    images_after_mllm_filter = []
    
    if mllm_filter:
        # Filter images: include if *any* selected MLLM is in the image's votes
        images_after_mllm_filter = [
            img_info for img_info in all_images_for_caption
            if any(vote in mllm_filter for vote in img_info.get("votes", []))
        ]
        st.info(f"Filtering images voted by: {', '.join(mllm_filter)}")
    else:
        images_after_mllm_filter = all_images_for_caption # Pass all if no MLLM filter
    
    # Apply vote count filter on top of MLLM filter results
    filtered_images = []
    if vote_count_filter:
        filtered_images = [
            img_info for img_info in images_after_mllm_filter
            if len(img_info.get("votes", [])) in vote_count_filter
        ]
        st.info(f"Filtering images with vote counts: {', '.join(map(str, vote_count_filter))}")
    else:
        filtered_images = images_after_mllm_filter # Pass all if no vote count filter    

    # --- Apply Score Sorting ---
    if st.session_state.score_sort_order and st.session_state.score_sort_order != "None":
        is_descending = st.session_state.score_sort_order == "Descending"
        try:
            # Sort images by score. Assumes 'score' is numeric or can be converted.
            # .get('score', 0.0) provides a default if 'score' key is missing (though load_data should prevent this)
            # and float() conversion handles scores stored as strings.
            filtered_images.sort(key=lambda img: float(img.get('score', 0.0)), reverse=is_descending)
            st.info(f"Sorting images by score ({st.session_state.score_sort_order}).")
        except (TypeError, ValueError) as e:
            st.warning(f"Could not sort by score. Ensure scores are numeric. Error: {e}")
            # If sorting fails, proceed with the list as it is (after other filters)

    total_images = len(filtered_images)
    total_pages = math.ceil(total_images / IMAGES_PER_PAGE)

    # st.markdown(f"**{total_images}** images found for this caption.")

    if total_images == 0:
        st.warning("No images associated with this caption.")
        if mllm_filter or vote_count_filter:
             st.warning("Try adjusting the filters in the sidebar.")
        else:
             st.stop() # Stop only if no images exist even without filters


    # --- Pagination Controls ---
    st.markdown(f"Displaying **{total_images}** images matching filter.")
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("⬅️ Previous", disabled=(st.session_state.current_page <= 1)):
            st.session_state.current_page -= 1
            st.rerun() # Rerun to reflect page change
    with col2:
        st.write(f"Page **{st.session_state.current_page}** of **{total_pages}**")
    with col3:
        if st.button("Next ➡️", disabled=(st.session_state.current_page >= total_pages)):
            st.session_state.current_page += 1
            st.rerun() # Rerun to reflect page change
    st.markdown("---")


    # --- Image Display and Annotation ---
    start_idx = (st.session_state.current_page - 1) * IMAGES_PER_PAGE
    end_idx = start_idx + IMAGES_PER_PAGE
    # images_to_display = images_for_caption[start_idx:end_idx]
    images_to_display = filtered_images[start_idx:end_idx] # Use the filtered list
   
    # Keep track of changes made on the current page view
    current_annotations = {}

    # Iterate through images in chunks for grid layout
    for i in range(0, len(images_to_display), IMAGES_PER_ROW):
        # Create columns for the current row
        cols = st.columns(IMAGES_PER_ROW)
        # Get the images for the current row
        row_images = images_to_display[i:i + IMAGES_PER_ROW]

        # Process each image in the row
        for j, img_info in enumerate(row_images):
            # Calculate the actual index relative to the full page list
            page_relative_index = i + j
            # Get the column for the current image
            with cols[j]:
                img_path = img_info.get("img_path", "N/A")
                votes = img_info.get("votes", [])
                current_annotation = img_info.get("human_annotation")
                score = img_info.get("score", 0.0) # Get score, defaults to 0.0 if not set by load_data


                # Determine the default display value dynamically if no annotation exists
                if current_annotation is not None:
                    default_display_value = current_annotation
                else:
                    # Apply dynamic default rules based on vote count
                    num_votes = len(votes)
                    if num_votes >= 3:
                        default_display_value = "True"
                    elif num_votes == 2:
                        default_display_value = "Ambiguous"
                    else: # 0 or 1 vote
                        default_display_value = "False"

                # Determine the index for the radio button based on the calculated default
                try:
                    default_index = ANNOTATION_OPTIONS.index(default_display_value)
                except ValueError:
                    default_index = 0 # Fallback to the first option ("True") if something unexpected happens

                # Display Image
                if os.path.exists(img_path):
                    try:
                        image = Image.open(img_path)
                        # Use a fixed width, height will adjust. Adjust width as needed.
                        st.image(image, width=250, caption=f"Index: {start_idx + page_relative_index} | Score: {score:.2f}")
                    except Exception as e:
                        st.warning(f"Could not load image: {img_path}. Error: {e}")
                else:
                    st.warning(f"Image not found at path: {img_path}")

                # Display Info
                st.markdown(f"**Path:** `{os.path.basename(img_path)}`") # Show only filename for brevity
                st.markdown(f"**Votes:** `{', '.join(votes) if votes else 'None'}`")

                # Annotation Radio Buttons
                radio_key = f"radio_{caption}_{img_path}_{start_idx + page_relative_index}"
                selected_choice = st.radio(
                    "Annotation:",
                    options=ANNOTATION_OPTIONS,
                    index=default_index,
                    key=radio_key,
                    horizontal=True
                )

                # Store the annotation choice
                current_annotations[page_relative_index] = selected_choice

        # Add a separator after each row of images


        st.markdown("---") # Separator between images

    # --- Save Button ---
    st.sidebar.markdown("---") # Add separator in sidebar
    if st.sidebar.button("💾 Update & Save Annotations", key="save_button"):
        # Apply the changes made on the current page to the session state data
        updated_count = 0
        # Iterate through the annotations made on the *current page*
        for page_relative_index, annotation_value in current_annotations.items():
             # Ensure the index is valid for the images displayed on this page
             if page_relative_index < len(images_to_display):
                 img_info_displayed = images_to_display[page_relative_index]
                 img_path_to_update = img_info_displayed.get("img_path")
             else:  # Should not happen, but safety check
                 st.sidebar.warning(f"Skipping update for an image with no path (Index {page_relative_index} on page).")
                 continue

             # Find the *original* image dictionary in the main session state data using its path
             original_data_list = st.session_state.annotation_data[caption]
             for original_img_info in original_data_list:
                 if original_img_info.get("img_path") == img_path_to_update:
                     if original_img_info.get("human_annotation") != annotation_value:
                         original_img_info["human_annotation"] = annotation_value
                 updated_count += 1

        if updated_count > 0:
            st.session_state.annotation_data[caption] = original_data_list
            st.sidebar.info(f"Updating {updated_count} annotations for caption '{caption}'...")
            # Save the entire data structure back to the file
            save_data(st.session_state.selected_annotation_file, st.session_state.annotation_data)
            # Optionally clear cache if you want the next load to reflect saved file directly
            # However, session_state holds the current truth, so cache clearing might not be strictly needed
            st.cache_data.clear()
            st.rerun() # Force a rerun to potentially show confirmation/clear state
        else:
            st.sidebar.warning("No changes detected on this page to save.")


else:
    st.info("Please select a caption from the sidebar to start annotating (after selecting a file).")


# --- Display Raw Data (Optional for Debugging) ---
st.sidebar.markdown("---")
if st.sidebar.checkbox("Show Raw Annotation Data", key="show_raw"):
    st.sidebar.json(st.session_state.annotation_data.get(st.session_state.selected_caption, "No caption selected"))