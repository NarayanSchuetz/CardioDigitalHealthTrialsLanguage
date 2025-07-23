import streamlit as st
import pandas as pd
import plotly.express as px
import pgeocode

FILENAME = 'ncts_with_zipcode_and_sponsor_type.csv'


# Set page config
st.set_page_config(page_title="Clinical Trials Analysis", layout="wide", initial_sidebar_state="collapsed")

# --- Stanford Color Palette ---
stanford_cardinal = "#8C1515"
stanford_cool_grey = "#53565A"
stanford_palo_alto_green = "#175E54"
stanford_palo_alto_blue = "#007C92" # Also Lagunita Blue
stanford_sky_blue = "#8F99A3"
stanford_light_grey = "#B1B4B6"
stanford_sandstone = "#D2C295"
stanford_poppy = "#E98300"
stanford_burnt_orange = "#B26F16"
stanford_stone = "#7F7776"

stanford_categorical = [
    stanford_cardinal,
    stanford_palo_alto_green,
    stanford_palo_alto_blue,
    stanford_poppy,
    stanford_sandstone,
    stanford_cool_grey,
    stanford_burnt_orange,
    stanford_stone,
    stanford_sky_blue,
    stanford_light_grey,
]

stanford_continuous = [
    [0.0, stanford_sandstone], # Start with Sandstone
    [0.5, stanford_poppy],       # Transition through Poppy
    [1.0, stanford_cardinal]    # End with Cardinal Red
]
# ------------------------------

# Helper function to safely parse sub-category values
def parse_sub_category(value):
    if pd.isna(value):
        return []
    if isinstance(value, list):
        return value
    if not isinstance(value, str):
        return []
    
    # Clean the string
    value = value.strip()
    if not value:
        return []
    
    # Handle different formats
    if value.startswith('[') and value.endswith(']'):
        # Handle list-like strings
        try:
            # Remove brackets and split by comma
            value = value[1:-1].strip()
            if not value:
                return []
            # Split by comma and clean each item
            items = [item.strip().strip("'\"") for item in value.split(',')]
            return [item for item in items if item]
        except:
            return []
    elif ',' in value:
        # Handle comma-separated strings
        items = [item.strip() for item in value.split(',')]
        return [item for item in items if item]
    else:
        # Handle single values
        return [value.strip()]

# Helper function to convert DataFrame to CSV for download
@st.cache_data
def convert_df_to_csv(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv(index=False).encode('utf-8')

# Initialize geocoder
nomi = pgeocode.Nominatim('us')

# Helper function to count other languages
@st.cache_data
def count_other_languages(df):
    if 'other_language_criteria' in df.columns:
        # Count non-empty entries
        total_with_other = df['other_language_criteria'].notna().sum()
        # Get all languages
        all_languages = df['other_language_criteria'].dropna().str.split(',').explode().str.strip()
        # Count total number of languages across all trials
        total_languages = len(all_languages)
        # Get unique languages and their counts
        language_counts = all_languages.value_counts()
        return total_with_other, total_languages, language_counts
    return 0, 0, pd.Series()

# Load original data for general analysis
@st.cache_data
def load_original_data():
    df = pd.read_csv(FILENAME, dtype={'first_zipcode': str})
    df.sponsor_type = df.sponsor_type.str.strip()
    return df

# Load and preprocess zipcode data for geographical analysis
@st.cache_data
def load_geographical_data():
    # Load the zipcode data
    df = load_original_data() #pd.read_csv(FILENAME)
    
    # Clean zip codes: Keep only 5 digits, handle NaN
    df['zip_clean'] = df['first_zipcode'].astype(str).str.extract(r'(\d{5})')
    df = df.dropna(subset=['zip_clean'])
    
    # Get unique zip codes and their states
    unique_zips = df['zip_clean'].unique()
    geo_data = nomi.query_postal_code(unique_zips.tolist())
    geo_data = geo_data[['postal_code', 'state_code']].dropna()
    
    # Create a mapping dictionary for zip to state
    zip_to_state = dict(zip(geo_data['postal_code'], geo_data['state_code']))
    
    # Map states to original dataframe
    df['state_code'] = df['zip_clean'].map(zip_to_state)
    
    return df

# Load data
original_df = load_original_data()
geo_df = load_geographical_data()

st.title("Clinical Trials Language Analysis")

def display_trial_categorization():
    st.header("Trial Categorization Analysis")
    
    # Display basic statistics
    st.subheader("Overview")
    st.metric("Total Trials Analyzed", len(original_df))
    st.divider()
    
    # Create visualization for trial categories
    st.subheader("Trial Categories Distribution")
    
    if 'category' in original_df.columns:
        # Create a pie chart
        category_counts = original_df['category'].value_counts()
        fig_cat_pie = px.pie(values=category_counts.values, 
                           names=category_counts.index,
                           title="Distribution of Trial Categories",
                           color_discrete_sequence=stanford_categorical)
        
        fig_cat_pie.update_traces(hoverinfo="label+percent+value")
        st.plotly_chart(fig_cat_pie, use_container_width=True, key="category_pie")
        
        # Create a selectbox for category selection
        selected_category = st.selectbox(
            "Filter by category:",
            ["All Categories"] + list(category_counts.index),
            key='cat_select' # Added key for uniqueness
        )
        st.divider()
        
        # Filter data based on selection
        if selected_category == "All Categories":
            filtered_df = original_df
        else:
            filtered_df = original_df[original_df['category'] == selected_category]
            st.write(f"Displaying statistics for: **{selected_category}**")
        
        # Add download button for the filtered data
        csv_cat = convert_df_to_csv(filtered_df)
        st.download_button(
            label=f"Download {selected_category} Data (CSV)",
            data=csv_cat,
            file_name=f'{selected_category.lower().replace(" ", "_")}_trials.csv',
            mime='text/csv',
            key='cat_download' # Added key
        )
        st.divider()
        
        # Calculate English inclusion/exclusion statistics
        st.subheader("English Language Criteria")
        col1, col2 = st.columns(2)
        
        with col1:
            english_included = filtered_df['english_is_inclusion'].sum() if 'english_is_inclusion' in filtered_df.columns else 0
            st.metric("Trials with English as Inclusion Criteria", english_included)
            if len(filtered_df) > 0:
                st.caption(f"{english_included/len(filtered_df)*100:.1f}% of selected trials")
        
        with col2:
            non_english_excluded = filtered_df['non_english_is_exclusion'].sum() if 'non_english_is_exclusion' in filtered_df.columns else 0
            st.metric("Trials with Non-English as Exclusion Criteria", non_english_excluded)
            if len(filtered_df) > 0:
                 st.caption(f"{non_english_excluded/len(filtered_df)*100:.1f}% of selected trials")
        st.divider()

        # Add other languages statistics
        st.subheader("Other Language Criteria")
        total_with_other, total_languages, language_counts = count_other_languages(filtered_df)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Trials with Add'l Languages", total_with_other)
            if len(filtered_df) > 0:
                st.caption(f"{total_with_other/len(filtered_df)*100:.1f}% of selected trials")
        with col2:
            st.metric("Total Add'l Languages Listed", total_languages)
        with col3:
            avg_langs = total_languages/total_with_other if total_with_other > 0 else 0
            st.metric("Avg Add'l Languages per Trial", f"{avg_langs:.1f}" if total_with_other > 0 else "N/A")
        st.divider()
        
        # Display individual languages
        if not language_counts.empty:
            st.subheader("Additionally Included Languages")
            # Create a DataFrame for the bar plot
            lang_df = pd.DataFrame({
                'Language': language_counts.index,
                'Number of Trials': language_counts.values,
                'Percentage': (language_counts.values / total_with_other * 100).round(1)
            })
            
            # Create bar plot
            fig_lang_bar = px.bar(
                lang_df.sort_values(by='Number of Trials', ascending=True), # Sort for better viz
                y='Language',
                x='Number of Trials',
                text='Percentage',
                title='Number of Trials by Language',
                labels={'Number of Trials': 'Number of Trials', 'Language': 'Language'},
                color='Number of Trials', # Keep color mapping to value
                color_continuous_scale=stanford_continuous, # Apply Stanford scale
                orientation='h'
            )
            
            # Update layout
            fig_lang_bar.update_layout(
                yaxis_title=None, # Cleaner look
                xaxis_title='Number of Trials',
                height=400 + (len(lang_df) * 20), # Dynamic height
                showlegend=False,
                coloraxis_showscale=False,
                margin=dict(l=120) # Ensure long language names fit
            )
            
            # Add percentage labels
            fig_lang_bar.update_traces(
                texttemplate='%{text}%',
                textposition='outside'
            )
            
            st.plotly_chart(fig_lang_bar, use_container_width=True, key="category_lang_bar")
            st.caption("Percentage shown is relative to trials with additional languages.")
    else:
        st.warning("Category column not found in the dataset. Please check the column names.")
        st.write("Available columns:", original_df.columns.tolist())

    # Add sub-category analysis section
    st.divider()
    st.subheader("Sub-Category Analysis")
    
    if 'sub_category' in original_df.columns:
        # Create a copy of the filtered dataframe and explode the sub-categories
        sub_cat_df = filtered_df.copy()
        sub_cat_df['sub_category'] = sub_cat_df['sub_category'].apply(parse_sub_category)
        sub_cat_df = sub_cat_df.explode('sub_category')
        
        # Create visualization for sub-categories
        st.subheader("Sub-Categories Distribution")
        st.write("We aimed to provide cardiovascular disease related sub-categories where appropriate. Please note that this was only possible for a subset of trials.")
        
        # Create a pie chart
        sub_cat_counts = sub_cat_df['sub_category'].value_counts()
        fig_sub_cat_pie = px.pie(values=sub_cat_counts.values, 
                               names=sub_cat_counts.index,
                               title="Distribution of Sub-Categories",
                               color_discrete_sequence=stanford_categorical)
        
        fig_sub_cat_pie.update_traces(hoverinfo="label+percent+value")
        st.plotly_chart(fig_sub_cat_pie, use_container_width=True, key="subcat_pie")
        
        # Create a selectbox for sub-category selection
        selected_sub_category = st.selectbox(
            "Filter by sub-category:",
            ["All Sub-Categories"] + list(sub_cat_counts.index),
            key='sub_cat_select'
        )
        st.divider()
        
        # Filter data based on sub-category selection
        if selected_sub_category == "All Sub-Categories":
            sub_cat_filtered_df = filtered_df
        else:
            sub_cat_filtered_df = filtered_df[filtered_df['sub_category'].apply(lambda x: selected_sub_category in parse_sub_category(x))]
            st.write(f"Displaying statistics for: **{selected_sub_category}**")
        
        # Calculate English inclusion/exclusion statistics for sub-category
        st.subheader("English Language Criteria")
        col1, col2 = st.columns(2)
        
        with col1:
            english_included = sub_cat_filtered_df['english_is_inclusion'].sum() if 'english_is_inclusion' in sub_cat_filtered_df.columns else 0
            st.metric("Trials with English as Inclusion Criteria", english_included)
            if len(sub_cat_filtered_df) > 0:
                st.caption(f"{english_included/len(sub_cat_filtered_df)*100:.1f}% of selected trials")
        
        with col2:
            non_english_excluded = sub_cat_filtered_df['non_english_is_exclusion'].sum() if 'non_english_is_exclusion' in sub_cat_filtered_df.columns else 0
            st.metric("Trials with Non-English as Exclusion Criteria", non_english_excluded)
            if len(sub_cat_filtered_df) > 0:
                st.caption(f"{non_english_excluded/len(sub_cat_filtered_df)*100:.1f}% of selected trials")
        st.divider()
        
        # Add other languages statistics for sub-category
        st.subheader("Other Language Criteria")
        total_with_other, total_languages, language_counts = count_other_languages(sub_cat_filtered_df)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Trials with Add'l Languages", total_with_other)
            if len(sub_cat_filtered_df) > 0:
                st.caption(f"{total_with_other/len(sub_cat_filtered_df)*100:.1f}% of selected trials")
        with col2:
            st.metric("Total Add'l Languages Listed", total_languages)
        with col3:
            avg_langs = total_languages/total_with_other if total_with_other > 0 else 0
            st.metric("Avg Add'l Languages per Trial", f"{avg_langs:.1f}" if total_with_other > 0 else "N/A")
        st.divider()
        
        # Display individual languages for sub-category
        if not language_counts.empty:
            st.subheader("Additionally Included Languages")
            # Create a DataFrame for the bar plot
            lang_df = pd.DataFrame({
                'Language': language_counts.index,
                'Number of Trials': language_counts.values,
                'Percentage': (language_counts.values / total_with_other * 100).round(1)
            })
            
            # Create bar plot
            fig_lang_bar = px.bar(
                lang_df.sort_values(by='Number of Trials', ascending=True),
                y='Language',
                x='Number of Trials',
                text='Percentage',
                title='Number of Trials by Language',
                labels={'Number of Trials': 'Number of Trials', 'Language': 'Language'},
                color='Number of Trials',
                color_continuous_scale=stanford_continuous,
                orientation='h'
            )
            
            # Update layout
            fig_lang_bar.update_layout(
                yaxis_title=None,
                xaxis_title='Number of Trials',
                height=400 + (len(lang_df) * 20),
                showlegend=False,
                coloraxis_showscale=False,
                margin=dict(l=120)
            )
            
            # Add percentage labels
            fig_lang_bar.update_traces(
                texttemplate='%{text}%',
                textposition='outside'
            )
            
            st.plotly_chart(fig_lang_bar, use_container_width=True, key="subcat_lang_bar")
            st.caption("Percentage shown is relative to trials with additional languages.")
            
            # Add download button for the sub-category filtered data
            csv_sub_cat = convert_df_to_csv(sub_cat_filtered_df)
            st.download_button(
                label=f"Download {selected_sub_category} Data (CSV)",
                data=csv_sub_cat,
                file_name=f'{selected_sub_category.lower().replace(" ", "_")}_trials.csv',
                mime='text/csv',
                key='sub_cat_download'
            )
    else:
        st.warning("Sub-category column not found in the dataset. Please check the column names.")
        st.write("Available columns:", original_df.columns.tolist())

def display_geographical_analysis():
    st.header("Geographical Distribution of Trials by State")
    if not geo_df.empty and 'state_code' in geo_df.columns:
        # Calculate frequency per state and filter for states with more than 5 trials
        state_counts_unfiltered = geo_df['state_code'].value_counts()
        states_to_show = state_counts_unfiltered[state_counts_unfiltered > 5].index
        geo_df_filtered = geo_df[geo_df['state_code'].isin(states_to_show)]

        # Calculate frequency per state for display, used for the dropdown selector later
        state_counts = geo_df_filtered['state_code'].value_counts().reset_index()
        state_counts.columns = ['state_code', 'count']

        # Define map options, only show percentage option if data is available
        map_options = ['Number of clinical trials']
        if 'english_is_inclusion' in geo_df_filtered.columns:
            map_options.append('Percentage of trials requiring English')

        # Add a radio button to select the metric
        metric_to_display = st.radio(
            "Select a metric to display on the map (states with >5 trials shown):",
            map_options,
            key='geo_metric_radio'
        )

        if metric_to_display == 'Number of clinical trials':
            display_data = state_counts
            color_col = 'count'
            map_title = 'Number of Clinical Trials by State'
            color_label = 'Number of Trials'
            range_color = None
        else:  # Percentage of trials requiring English
            # Calculate English inclusion statistics per state from the filtered dataframe
            state_english_stats = geo_df_filtered.groupby('state_code')['english_is_inclusion'].agg(
                included_english='sum',
                total_trials='count'
            ).reset_index()
            state_english_stats['percentage'] = (state_english_stats['included_english'] / state_english_stats['total_trials']) * 100
            
            display_data = state_english_stats
            color_col = 'percentage'
            map_title = 'Percentage of Trials Requiring English by State'
            color_label = '% Requiring English'
            range_color = [0, 100]

        # Create choropleth map
        fig_map = px.choropleth(
            display_data,
            locations='state_code',
            locationmode='USA-states',
            color=color_col,
            scope='usa',
            title=map_title,
            color_continuous_scale=stanford_continuous, # Apply Stanford scale
            labels={color_col: color_label, 'state_code': 'State'},
            range_color=range_color
        )
        
        # Update layout for better visualization
        fig_map.update_layout(
            geo=dict(
                lakecolor='rgb(255, 255, 255)',
                landcolor='rgb(217, 217, 217)',
            ),
            margin={"r":0,"t":40,"l":0,"b":0} # Adjusted top margin
        )
        
        # Display the map
        st.plotly_chart(fig_map, use_container_width=True, key="state_map")
        st.divider()
        
        # Add state selection
        selected_state = st.selectbox(
            "Select a state to view detailed statistics:",
            ["All States"] + sorted(state_counts['state_code'].tolist()),
            key='state_select' # Added key for uniqueness
        )
        
        # Show statistics for selected state or all states
        if selected_state == "All States":
            st.subheader("Overall Statistics (All Shown States)")
            state_trial_ids = geo_df_filtered.index.tolist()
            state_trials_original = original_df.loc[original_df.index.intersection(state_trial_ids)]
            total_trials = len(state_trials_original)
        else:
            # Get trials for selected state
            state_trials_geo = geo_df_filtered[geo_df_filtered['state_code'] == selected_state]
            state_trial_ids = state_trials_geo.index.tolist()
            
            # Get corresponding trials from original dataset
            # Ensure index alignment
            state_trials_original = original_df.loc[original_df.index.intersection(state_trial_ids)]
            total_trials = len(state_trials_original)
            st.subheader(f"Statistics for {selected_state}")
        
        if total_trials > 0:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Trials in Selection", total_trials)
            with col2:
                percentage = (total_trials / len(original_df)) * 100
                st.metric("Percentage of All Trials", f"{percentage:.1f}%")

            # Add download button for the state/all data
            csv_state = convert_df_to_csv(state_trials_original)
            st.download_button(
                label=f"Download {selected_state} Data (CSV)",
                data=csv_state,
                file_name=f'{selected_state.lower().replace(" ", "_")}_trials.csv',
                mime='text/csv',
                key='state_download' # Added key
            )
            st.divider()
            
            # English language statistics
            st.subheader("English Language Criteria in Selection")
            col1, col2 = st.columns(2)
            
            with col1:
                english_included = state_trials_original['english_is_inclusion'].sum() if 'english_is_inclusion' in state_trials_original.columns else 0
                st.metric("Trials with English as Inclusion Criteria", english_included)
                st.caption(f"{english_included/total_trials*100:.1f}% of selected trials")
            
            with col2:
                non_english_excluded = state_trials_original['non_english_is_exclusion'].sum() if 'non_english_is_exclusion' in state_trials_original.columns else 0
                st.metric("Trials with Non-English as Exclusion Criteria", non_english_excluded)
                st.caption(f"{non_english_excluded/total_trials*100:.1f}% of selected trials")
            st.divider()
            
            # Add other languages statistics for the selection
            st.subheader("Other Language Criteria in Selection")
            total_with_other, total_languages, language_counts = count_other_languages(state_trials_original)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Trials with Add'l Languages", total_with_other)
                st.caption(f"{total_with_other/total_trials*100:.1f}% of selected trials")
            with col2:
                st.metric("Total Add'l Languages Listed", total_languages)
            with col3:
                avg_langs = total_languages/total_with_other if total_with_other > 0 else 0
                st.metric("Avg Add'l Languages per Trial", f"{avg_langs:.1f}" if total_with_other > 0 else "N/A")
            st.divider()
                
            # Display individual languages for the state/selection
            if not language_counts.empty:
                st.subheader(f"Language Distribution in Selection")
                # Create a DataFrame for the bar plot
                lang_df = pd.DataFrame({
                    'Language': language_counts.index,
                    'Number of Trials': language_counts.values,
                    'Percentage': (language_counts.values / total_with_other * 100).round(1)
                })
                
                # Create bar plot
                fig_state_lang_bar = px.bar(
                    lang_df.sort_values(by='Number of Trials', ascending=True), # Sort for better viz
                    y='Language',
                    x='Number of Trials',
                    text='Percentage',
                    title=f'Number of Trials by Language in {selected_state}',
                    labels={'Number of Trials': 'Number of Trials', 'Language': 'Language'},
                    color='Number of Trials', # Keep color mapping to value
                    color_continuous_scale=stanford_continuous, # Apply Stanford scale
                    orientation='h'
                )
                
                # Update layout
                fig_state_lang_bar.update_layout(
                    yaxis_title=None, # Cleaner look
                    xaxis_title='Number of Trials',
                    height=400 + (len(lang_df) * 20), # Dynamic height
                    showlegend=False,
                    coloraxis_showscale=False,
                    margin=dict(l=120) # Ensure long language names fit
                )
                
                # Add percentage labels
                fig_state_lang_bar.update_traces(
                    texttemplate='%{text}%',
                    textposition='outside'
                )
                
                st.plotly_chart(fig_state_lang_bar, use_container_width=True, key="state_lang_bar")
                st.caption("Percentage shown is relative to trials with additional languages in the current selection.")
        else:
            st.info(f"No trials found for {selected_state}.")
            
    else:
        st.warning("Could not generate map. Ensure 'first_zipcode' column exists and contains valid US zip codes.")

def display_sponsor_analysis():
    st.header("Sponsor Type Analysis")
    st.write("This section analyzes language criteria based on the type of trial sponsor (Academic vs. Industry).")
    
    if 'sponsor_type' not in original_df.columns:
        st.warning("Sponsor type column not found. Please ensure 'sponsor_type' is in the dataset.")
        return

    # Filter out 'Unknown' or NaN sponsor types for a cleaner comparison
    sponsor_df = original_df.copy()
    #sponsor_df.sponsor_type = sponsor_df.sponsor_type.str.strip()

    st.subheader("Distribution of Sponsor Types")
    sponsor_counts = sponsor_df['sponsor_type'].value_counts()
    fig_sponsor_pie = px.pie(
        values=sponsor_counts.values, 
        names=sponsor_counts.index,
        title="Distribution of Sponsor Types (Academic vs. Industry)",
        color_discrete_sequence=stanford_categorical
    )
    fig_sponsor_pie.update_traces(hoverinfo="label+percent+value")
    st.plotly_chart(fig_sponsor_pie, use_container_width=True, key="sponsor_pie")
    st.divider()

    st.subheader("Language Criteria by Sponsor Type")
    
    # Group by sponsor_type and calculate percentages
    sponsor_lang_stats = sponsor_df.groupby('sponsor_type').agg(
        total_trials=('sponsor_type', 'count'),
        english_inclusion=('english_is_inclusion', 'sum'),
        non_english_exclusion=('non_english_is_exclusion', 'sum')
    ).reset_index()

    sponsor_lang_stats['english_inclusion_pct'] = (sponsor_lang_stats['english_inclusion'] / sponsor_lang_stats['total_trials']) * 100
    sponsor_lang_stats['non_english_exclusion_pct'] = (sponsor_lang_stats['non_english_exclusion'] / sponsor_lang_stats['total_trials']) * 100

    # Melt the dataframe for plotting
    stats_to_plot = sponsor_lang_stats.melt(
        id_vars=['sponsor_type', 'total_trials'],
        value_vars=['english_inclusion_pct', 'non_english_exclusion_pct'],
        var_name='criteria',
        value_name='percentage'
    )
    
    stats_to_plot['criteria'] = stats_to_plot['criteria'].map({
        'english_inclusion_pct': 'English as Inclusion',
        'non_english_exclusion_pct': 'Non-English as Exclusion'
    })

    # Create the grouped bar chart
    fig_sponsor_lang = px.bar(
        stats_to_plot,
        x='sponsor_type',
        y='percentage',
        color='criteria',
        barmode='group',
        title='Language Criteria by Sponsor Type',
        labels={'sponsor_type': 'Sponsor Type', 'percentage': 'Percentage of Trials (%)', 'criteria': 'Language Criterion'},
        color_discrete_map={
            'English as Inclusion': stanford_cardinal,
            'Non-English as Exclusion': stanford_palo_alto_blue
        },
        text=stats_to_plot['percentage'].apply(lambda x: f'{x:.1f}%')
    )

    fig_sponsor_lang.update_traces(textposition='outside')
    fig_sponsor_lang.update_layout(
        yaxis_title='Percentage of Trials',
        xaxis_title=None,
        legend_title='Language Criterion',
        uniformtext_minsize=8, 
        uniformtext_mode='hide'
    )
    
    st.plotly_chart(fig_sponsor_lang, use_container_width=True, key="sponsor_lang_bar")
    
    st.write("""
    This chart compares the percentage of trials broken down by whether the sponsor is academic or from industry. No statistical significant difference was found between the distributions of trials sponsored by academic and industry sponsors.
    - **English as Inclusion**: The percentage of trials requiring English proficiency.
    - **Non-English as Exclusion**: The percentage of trials excluding non-English speakers.
    """)
    st.divider()
    
    # Display raw numbers and download option
    st.subheader("Detailed Data by Sponsor Type")
    st.dataframe(sponsor_lang_stats, use_container_width=True)

    csv_sponsor = convert_df_to_csv(sponsor_lang_stats)
    st.download_button(
        label="Download Sponsor Analysis Data (CSV)",
        data=csv_sponsor,
        file_name='sponsor_language_analysis.csv',
        mime='text/csv',
        key='sponsor_download'
    )

def display_methods():
    st.header("Methods")
    
    # Display flowchart at the top
    with open("FlowChart_v3.svg", "r") as f:
        svg = f.read()
    st.markdown(svg, unsafe_allow_html=True)
    
    st.subheader("Data Acquisition and Initial Processing")
    st.write("""
    An initial dataset comprising 1,986 clinical trials, identified by their National Clinical Trial (NCT) numbers, was obtained from "clinicaltrials.gov" based on the following query (metabolic syndrome OR obesity OR overweight OR weight OR diet OR nutrition OR prediabetes OR pre-diabetes OR diabetes OR prehypertension OR hypertension or dyslipidemia OR hyperlipidemia OR heart disease OR coronary artery disease OR atherosclerotic vascular disease OR coronary atherosclerosis OR atherosclerosis, coronary OR atherosclerosis OR atheroscleroses OR atheromatosis OR cardiovascular OR peripheral artery disease OR physical activity OR exercise OR sedentary OR healthy OR lifestyle factors OR heart failure OR atrial fibrillation OR atrial flutter OR arrhythmia | digital therapeutic OR digital therapy OR digital therapies OR mobile health OR smartphone OR smart phone OR digital intervention OR mobile platform OR mobile app OR mobile device OR study app OR digital treatment OR android OR app OR app. OR app, OR digital tablet OR iOS OR iPhone OR smartwatch OR smartwatch OR virtual reality OR video game OR digital health OR mobile video OR digital platform OR software intervention OR software treatment | In United States | Adult (18 - 64), Older adult (65+) | Accepts healthy volunteers | Interventional studies). An automated procedure using natural language processing was employed to extract the participant inclusion and exclusion criteria text for each trial record from their web entry. This extraction process was subject to occasional errors, leading to incomplete criteria data for a subset of trials. Following this initial data collection and extraction, a manual curation step was performed, resulting in the removal of 498 trials that studied a pediatric population and those whose primary subject area was in either cancer or neurologic disorders. This yielded an intermediate working dataset of 1,488 clinical trial records.
    """)
    
    st.subheader("Language Criteria Extraction and Refinement")
    st.write("""
    The extracted inclusion and exclusion criteria texts for the 1,488 trials were processed using natural language processing for each trial record from their web entry on ClinicalTrials.gov. This extraction process was subject to occasional errors, leading to incomplete criteria data for a subset of trials. An initial analysis of this automated extraction output was performed to identify trials where criteria extraction was incomplete (i.e., both inclusion and exclusion fields were blank, or only one was populated). For these identified trials, the complete inclusion and exclusion criteria were manually retrieved from ClinicaTrials.gov and integrated into the dataset. Subsequently, the language criteria extraction process was re-executed on the fully populated dataset of 1,488 trials to ensure consistent analysis.
    """)
    
    st.subheader("Trial Categorization and Feature Identification")
    st.write("""
    Each of the 1,488 trials was then subjected to automated categorization. This analysis utilized the structured 'Conditions' field and the free-text 'Brief Description' associated with each trial record. Trials were assigned to one of several predefined main categories: Metabolic & Weight-Related Disorders, Cardiovascular Diseases, Cancers, Lifestyle & Behavioral Factors, Neurocognitive & Mental Health, or Other / Special Populations. Trials categorized under Cardiovascular Diseases were further sub-categorized into specific conditions (hypertension, heart failure, atrial fibrillation, stroke, other heart disease) using the same NLP-based approach applied to the trial descriptions.
    
    Concurrently, this analysis assessed the trial descriptions to identify studies employing digital health technologies (defined by the mention of smartphones, wearables, or tablets).
    """)
    
    st.subheader("Final Cohort Selection")
    st.write("""
    Based on the primary research focus, a final selection filter was applied to the categorized dataset. Only trials assigned to the main categories of "Metabolic & Weight-Related Disorders," "Cardiovascular Diseases," or "Lifestyle & Behavioral Factors" were retained for the final analysis. This step excluded 296 trials, resulting in a final analytic cohort of 1,192 clinical trials.
    """)

    st.subheader("Validation of NLP Pipeline for Inclusion/Exclusion Criteria Extraction")
    st.write("""
    To validate the accuracy of the NLP pipeline for inclusion/exclusion criteria extraction, a subset of 99 trials was manually reviewed by directly referencing the trial record on ClinicalTrials.gov. The performance of the pipeline was evaluated for two key tasks: identifying 'English language proficiency' as an inclusion criterion and identifying 'non-English language proficiency' as an exclusion criterion.

    The pipeline demonstrated high accuracy for both tasks. For identifying English as an inclusion criterion, it achieved a balanced accuracy of 0.9872 and an F1-score of 0.9870. For identifying non-English as an exclusion criterion, it achieved a balanced accuracy of 0.9502 and an F1-score of 0.9286. Detailed performance metrics are presented in the table below.
    Two of the errors in the Non-English as exclusion criteria were once due to wrongfully extracting an inclusion criterion as an exclusion criterion and once due to ambiguous language in the criteria text, which the manual rater noted as potentially unclear.
    """)

    # Create a dataframe for the performance metrics
    perf_data = {
        'Metric': ['Balanced Accuracy', 'F1 Score', 'Precision', 'Recall', 'ROC AUC'],
        'English is Inclusion Criteria': [0.9872, 0.9870, 1.0000, 0.9744, 0.9872],
        'Non-English is Exclusion Criteria': [0.9502, 0.9286, 0.9286, 0.9286, 0.9502]
    }
    perf_df = pd.DataFrame(perf_data).set_index('Metric')
    st.dataframe(perf_df, use_container_width=True)

    st.image(
        "confusion_matrix_english_is_inclusion.png",
        caption="Confusion matrix for the validation of the NLP pipeline in identifying 'English language proficiency' as an inclusion criterion.",
        width=768
    )
    st.image(
        "confusion_matrix_non_english_exclusion.png",
        caption="Confusion matrix for the validation of the NLP pipeline in identifying 'non-English language proficiency' as an exclusion criterion.",
        width=768
    )

    st.subheader("Analysis of Sponser Type on Language Criteria")
    st.write("""
    To analyze whether academic vs industry sponsored trials have differing language inclusion/exclusion criteria, we compared the language criteria of trials sponsored by industry and trials sponsored by academic institutions.
    To assign sponsor type to each trial, we used a semi-automated approach based on a keyword search of the sponsor and manual review of ambiguous instances, as outlined in the following guidelines:

    **Industry Sponsors**
    - Pharmaceutical companies (e.g., Amgen, AstraZeneca, Bayer)
    - Medical device manufacturers (e.g., Abbott Medical Devices, Becton Dickinson)
    - Technology companies (e.g., Apple Inc., AliveCor)
    - Private healthcare organizations and for-profit hospitals
    - Private research organizations/CROs
    - Biotechnology companies
    - Companies with "Inc.", "Corp.", "LLC", "Ltd." in name (unless clearly academic)

    **Academic Sponsors**
    - Universities and colleges (e.g., Arizona State University, Baylor College of Medicine)
    - Academic medical centers affiliated with universities
    - Government research institutes (NIH, CDC, etc.)
    - Non-profit research foundations
    - Public hospitals and health systems
    - Professional medical associations
    - Educational institutions

    **Classification Rules**
    1. If "University", "College", "Institute" appears in an academic context → Academic
    2. If clearly a company name with corporate suffix → Industry
    3. If a medical center affiliated with a university → Academic
    4. If a private for-profit healthcare organization → Industry
    5. If government agency or public institution → Academic
    6. Remaining cases set to unknown and reviewed manually

    **Treatment of Special Cases (Manual Review)**
    - Research institutes can be either academic or industry depending on whether they are for-profit (industry) or not (academic).
    - Health systems can be academic (non-profit) or industry (for-profit)
    - Individual natural persons as sponsors were treated as academic
    """)
    
    st.write("""
    **Statistical Comparison between Distributions**
        Statistical significance of the inclusion exclusion distribution between academia and industry was tested using a chi-squared test at a 0.05 significance level and 1 degree of freedom. For non-english as exclusion criteria, this resulted in a Chi-square statistic: 1.2323
with a p-value: 0.2670. For english as inclusion criteria, this resulted in a Chi-square statistic: 0.0769 with a p-value: 0.7815.
    """)

# Use a radio button for navigation that preserves state across reruns
selected_tab = st.radio(
    "Navigation",
    ["Trial Categorization", "Geographical Analysis", "Sponsor Analysis", "Methods"],
    horizontal=True,
    label_visibility="collapsed",
)

if selected_tab == "Trial Categorization":
    display_trial_categorization()
elif selected_tab == "Geographical Analysis":
    display_geographical_analysis()
elif selected_tab == "Sponsor Analysis":
    display_sponsor_analysis()
else:
    display_methods()
