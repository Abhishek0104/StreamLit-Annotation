import streamlit as st
import json
import os
from PIL import Image
import math

# --- Page Config (MUST be the first Streamlit command) ---
st.set_page_config(layout="wide") # Use wide layout for more space

# --- Configuration ---
JSON_FILE_PATH = 'annotations_input.json'
IMAGES_PER_PAGE = 10  # Number of images to display per page
ANNOTATION_OPTIONS = ["True", "False", "Ambiguous"]
DEFAULT_ANNOTATION = "Ambiguous" # As requested, default to True

# --- Helper Functions ---

@st.cache_data # Cache the data loading to avoid reloading on every interaction
def load_data(json_path):
    """Loads the annotation data from the JSON file."""
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        # Initialize human_annotation if it doesn't exist
        for caption, images in data.items():
            for img_info in images:
                if "human_annotation" not in img_info:
                    img_info["human_annotation"] = None # Start with None, will default display to True later
        return data
    except FileNotFoundError:
        st.error(f"Error: JSON file not found at {json_path}")
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
    """Saves the updated annotation data back to the JSON file."""
    try:
        # Make a copy before saving to avoid modifying the cached version directly
        data_to_save = data.copy()
        with open(json_path, 'w') as f:
            json.dump(data_to_save, f, indent=2) # Use indent for readability
        st.success(f"Annotations successfully saved to {json_path}!")
    except Exception as e:
        st.error(f"Error saving data to {json_path}: {e}")

# --- Initialize Session State ---
if 'annotation_data' not in st.session_state:
    st.session_state.annotation_data = load_data(JSON_FILE_PATH)

if 'selected_caption' not in st.session_state:
    st.session_state.selected_caption = None

if 'current_page' not in st.session_state:
    st.session_state.current_page = 1

if 'selected_mllms' not in st.session_state:
    st.session_state.selected_mllms = [] # Initialize empty list for MLLM filter

if 'selected_vote_counts' not in st.session_state:
    st.session_state.selected_vote_counts = [] # Initialize empty list for vote count filter

# --- Main App Logic ---
# st.set_page_config(layout="wide") # Use wide layout for more space
st.title("MLLM Annotation Verification Tool")

# Ensure data is loaded
if st.session_state.annotation_data is None:
    st.stop() # Stop execution if data loading failed

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

    for i, img_info in enumerate(images_to_display):
        img_path = img_info.get("img_path", "N/A")
        votes = img_info.get("votes", [])
        # Use the existing human annotation if available, otherwise default
        # The actual default radio selection happens below using the 'index' parameter
        current_annotation = img_info.get("human_annotation")

        # Determine the index for the radio button based on the current annotation
        # Default to "True" if no human annotation exists yet
        default_display_value = current_annotation if current_annotation is not None else DEFAULT_ANNOTATION
        try:
            default_index = ANNOTATION_OPTIONS.index(default_display_value)
        except ValueError:
            default_index = ANNOTATION_OPTIONS.index(DEFAULT_ANNOTATION) # Fallback if value is somehow invalid

        # Use columns for better layout per image
        col_img, col_info = st.columns([1, 2])

        with col_img:
            if os.path.exists(img_path):
                try:
                    # Display image with controlled width
                    image = Image.open(img_path)
                    st.image(image, width=300, caption=f"Index: {start_idx + i}") # Smaller width
                except Exception as e:
                    st.warning(f"Could not load image: {img_path}. Error: {e}")
            else:
                st.warning(f"Image not found at path: {img_path}")

        with col_info:
            st.markdown(f"**Image Path:** `{img_path}`")
            st.markdown(f"**MLLM Votes:** `{', '.join(votes) if votes else 'None'}`")

            # Generate a unique key for each radio button based on image path and caption
            # This ensures widget state is preserved correctly by Streamlit
            radio_key = f"radio_{caption}_{img_path}_{start_idx + i}"

            # Use st.radio for annotation selection
            selected_choice = st.radio(
                "Your Annotation:",
                options=ANNOTATION_OPTIONS,
                index=default_index, # Set default based on current/default annotation
                key=radio_key,
                horizontal=True # Display options horizontally
            )

            # Store the selected choice to update the main data structure later
            # We store the index *relative to the currently displayed page*
            # and the image path for robust saving later.
            page_relative_index = i
            current_annotations[page_relative_index] = selected_choice
            # current_annotations[original_list_index] = selected_choice


        st.markdown("---") # Separator between images

    # --- Save Button ---
    st.sidebar.markdown("---") # Add separator in sidebar
    if st.sidebar.button("💾 Update & Save Annotations", key="save_button"):
        # Apply the changes made on the current page to the session state data
        updated_count = 0
        # Iterate through the annotations made on the *current page*
        for page_relative_index, annotation_value in current_annotations.items():
             # Get the actual image info dictionary from the displayed list
             img_info_displayed = images_to_display[page_relative_index]
             img_path_to_update = img_info_displayed.get("img_path")

             if not img_path_to_update:
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
            st.sidebar.info(f"Updating {updated_count} annotations for caption '{caption}'...")
            # Save the entire data structure back to the file
            save_data(JSON_FILE_PATH, st.session_state.annotation_data)
            # Optionally clear cache if you want the next load to reflect saved file directly
            # However, session_state holds the current truth, so cache clearing might not be strictly needed
            # st.cache_data.clear()
            # st.rerun() # Force a rerun to potentially show confirmation/clear state
        else:
            st.sidebar.warning("No changes detected on this page to save.")


else:
    st.info("Please select a caption from the sidebar to start annotating.")


# --- Display Raw Data (Optional for Debugging) ---
st.sidebar.markdown("---")
if st.sidebar.checkbox("Show Raw Annotation Data", key="show_raw"):
    st.sidebar.json(st.session_state.annotation_data.get(st.session_state.selected_caption, "No caption selected"))