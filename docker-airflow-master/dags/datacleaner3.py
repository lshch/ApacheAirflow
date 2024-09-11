def extract_data(file_path, **kwargs):
    import pandas as pd
    try:
        df = pd.read_csv(file_path)
        kwargs['ti'].xcom_push(key='extracted_data', value=df.to_dict())
    except FileNotFoundError:
        raise ValueError(f"File not found: {file_path}")
    except Exception as e:
        raise ValueError(f"Error reading file: {e}")



def transform_data(**kwargs):
    import pandas as pd

    df = kwargs['ti'].xcom_pull(key='extracted_data')
    # Apply transformation logic here
    # Handling Missing Values in Specific Columns
    # Fill missing values in 'name' and 'host_name' with 'Unknown'

    def handle_incompatible_characters(df):
        
        # Function to remove incompatible characters and transcode to UTF-8
        def normalize_and_remove_incompatible(text_obj):
            import re
            import unicodedata
            text = '-- ' + str(text_obj)
            #try:
                # Convert to Unicode and normalize
            unicode_text = unicodedata.normalize('NFKC', str(text))
                # Remove non-printable characters (adjust regex as needed)
            unicode_text = unicode_text + ' -- '
            cleaned_text = re.sub(r'[^\x20-\x7E]', '', unicode_text)
            
            return cleaned_text
            #except Exception as e:
            #    # Handle exceptions gracefully (e.g., log or return an empty string)
            #    print(f"Error processing text: {e}")
            #    return ""

        df['name'] = df['name'].apply(normalize_and_remove_incompatible)
        df.to_csv('~/store_files_airflow2/df_after_handle_incompatible_characters_data.csv', index=True)

        return df
    


    def handle_miising_values(df):
        df.loc[:, 'name'] = df['name'].fillna('Unknown')
        df.loc[:, 'host_name'] = df['host_name'].fillna('Unknown')
        return df
    
    # Filter out rows where price is 0 or negative
    def filter_where_price_is_more_0 (df):
        df = df[df['price'] > 0]
        return df
    
    # Convert 'last_review' to datetime format
    def convert_last_review_to_datetime(df):
        df['last_review'] = pd.to_datetime(df['last_review'])
        return df
    
    # Handle missing (if any) last_review dates by filling them with the earliest 
    # date in the dataset or a default date.
    def handle_missing_last_review(df, default_date=pd.Timestamp('1900-01-01')):
        # Fill missing values with the earliest date in the dataset or the default date
        df['last_review'] = df['last_review'].fillna(
        df['last_review'].min() or default_date)
        return df
    
    # Handle missing values in reviews_per_month by filling them with 0.
    def handle_missing_reviews_per_month(df):
        # Fill missing values with 0
        df['reviews_per_month'] = df['reviews_per_month'].fillna(0)
        return df

    # Drop any rows(if any) with missing latitude or longitude values.
    def drop_rows_with_missing_location(df):
        # Drop rows with missing latitude or longitude values
        df = df.dropna(subset=['latitude', 'longitude'])
        return df
    
    def remove_invalid_numeric_columns(df, columns):
        # Create a copy of the DataFrame to avoid modifying the original
        df_cleaned = df.copy()

        # Iterate over each column
        for col in columns:
            # Check if the column's data type is numeric
            if not pd.api.types.is_numeric_dtype(df_cleaned[col]):
            # Remove rows with non-numeric values
                df_cleaned = df_cleaned[pd.to_numeric(df_cleaned[col], errors='coerce').notnull()]

        return df_cleaned
    
    def clean_and_transform(df):
        df = handle_incompatible_characters(df) 
        df = remove_invalid_numeric_columns(df, ['latitude', 'number_of_reviews'])
        df = handle_miising_values(df)
        df = filter_where_price_is_more_0 (df)
        df = convert_last_review_to_datetime(df)
        df = handle_missing_last_review(df, default_date=pd.Timestamp('2019-01-01'))
        df = handle_missing_reviews_per_month(df) 
        df = drop_rows_with_missing_location(df)
        df.to_csv('~/store_files_airflow_transformed/clean_AB_NYC_2019.csv', index=False)
        return df
  
    data_dict = kwargs['ti'].xcom_pull(key='extracted_data')  # Assuming DataFrame is pulled

    # Check if it's a dictionary and convert it to a DataFrame
    if isinstance(data_dict, dict):
        df = pd.DataFrame(data_dict)
    else:
        df = data_dict  # If it's already a DataFram


    transformed_df = clean_and_transform(df)
    kwargs['ti'].xcom_push(key='transformed_data', value=transformed_df.to_dict())


def check_data_quality(**kwargs):
    # Import libraries
    import pandas as pd
    from sqlalchemy import create_engine
    from airflow import settings

    # Connect to database
    mysql_conn_id = "mysql_conn2"  
    #connection = settings.get_connection(mysql_conn_id)
    #mysql_password = connection.password
    from sqlalchemy import create_engine
    mysql_url = 'mysql+pymysql://root:root@mysql:3306/mysql'
    engine = create_engine(mysql_url)

    #engine = create_engine(f"mysql+pymysql://airflow:{mysql_password}@airflow-mysql/{mysql_conn_id}")
    

    # Get expected record count from transformed data
    expected_records = kwargs['ti'].xcom_pull(key='transformed_data')

    # Get actual record count from table
    sql = f"SELECT COUNT(*) FROM airbnb_listings"
    actual_records = pd.read_sql_query(sql, engine).iloc[0][0]

    # Check for null values in specified columns
    null_value_check = engine.execute(f"SELECT * FROM airbnb_listings WHERE price IS NULL OR minimum_nights IS NULL OR availability_365 IS NULL").rowcount

    # Raise errors if checks fail
    if expected_records != actual_records:
        raise ValueError(f"Record count mismatch. Expected: {expected_records}, Actual: {actual_records}")
    elif null_value_check > 0:
        raise ValueError(f"Null values found in price, minimum_nights, or availability_365 columns.")

    # If all checks pass, return success
    return True


