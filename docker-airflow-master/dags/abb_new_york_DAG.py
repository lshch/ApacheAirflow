from airflow import DAG
from datetime import datetime, timedelta
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator
from airflow.operators.mysql_operator import MySqlOperator
from airflow.operators.email_operator import EmailOperator

import unicodedata
import chardet


from datacleaner3 import extract_data
from datacleaner3 import transform_data
from datacleaner3 import check_data_quality


yesterday_date = datetime.strftime(datetime.now() - timedelta(1), '%Y-%m-%d')

default_args = {
    'owner': 'Airflow',
    'start_date': datetime(2024, 9, 11),
    'retries': 1,
    'retry_delay': timedelta(seconds=5)
}

with DAG(
    'abb_new_york_dag', 
    default_args=default_args,
    schedule_interval='@daily', 
    template_searchpath=['/usr/local/airflow/sql_files2'], 
    catchup=True
) as dag:

    check_file_exists=BashOperator(task_id='check_file_exists', bash_command='shasum ~/store_files_airflow2/AB_NYC_2019.csv', retries=2, retry_delay=timedelta(seconds=15), dag=dag)
    
    drop_my_sql_tables = MySqlOperator(task_id='drop_my_sql_tables', mysql_conn_id="mysql_conn2", sql="drop_tables2.sql", dag=dag)

    create_mysql_table_airbnb_listings = MySqlOperator(task_id='create_mysql_table_airbnb_listings', mysql_conn_id="mysql_conn2", sql="create_table3.sql", dag=dag)
    
    extract_task = PythonOperator(task_id='extract_data', python_callable=extract_data, op_kwargs={'file_path': '~/store_files_airflow2/AB_NYC_2019.csv'}, provide_context=True, dag=dag)

    transform_task = PythonOperator(task_id='transform_data', python_callable=transform_data, provide_context=True, dag=dag)

    insert_into_table = MySqlOperator(task_id='insert_into_table', mysql_conn_id="mysql_conn2", sql="insert_into_table3.sql")
   
    data_quality_check = PythonOperator(
    task_id='data_quality_check',
    python_callable=check_data_quality,
    provide_context=True,
    dag=dag
    )

    check_file_exists >> drop_my_sql_tables >> [create_mysql_table_airbnb_listings, extract_task] >> transform_task >> insert_into_table >> data_quality_check 