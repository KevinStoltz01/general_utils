import os
import datetime
import glob
from pathlib import Path
import numpy as np
import pandas as pd
import pyodbc
import requests
import scipy.stats
import seaborn as sns
from sqlalchemy import create_engine
import time
import urllib.parse
import pyexasol
import getpass

import win32com.client as win32

pd.set_option('precision', 11)


class ETL():
    
    '''
    A class for setting up an ETL workflow. Includes ODBC connection, writing to test server, reading
    and saving flat files.
    
    Parameters
    ----------
    
    project: str
        An existing project folder structured to NAM SCM R&A specifications. 
        
    user: str
        'main' for projects_main or your name for your personal directory. 
        
    servers: str or list
        DB servers to be connected to via ODBC. Defaults are 04 and 03. 
        
        If one en needs connections to multiple tables, that server name must be passed multiple times. 
        i.e. if connecting to PDX_SAP_USER and RBK_USER on 04 input must be [PDX_SAP_USER, PDX_SAP_USER].
        
    dbs: str or list
        Individual database connections to be made via ODBC. i.e. PDX_SAP_USER, ADI_USER_MAINTAINED, etc.
        
    system: str
        Designates Windows or Linux file path conventions. Default is Windows.
        
        
    Returns
    -------
    
    ETL Object
    
        Mapped to project folder, ODBC connections.
        
    '''
    
    def __init__(self, 
                 project, 
                 user="Kevin",
                 onedrive_wd = "NAM_SCM_RnA_RnD - Documents",
                 system="linux"):
        
        super().__init__()
        self.user = user.title()
        self.project = project
        self.servers = servers
                
        try:
            self.dbs = dbs.upper()
        except:
            self.dbs = [x.upper() for x in dbs]
     
        self.cnxns = {}    
        self.system = system
        self.onedrive_wd = onedrive_wd
        self.paths = self.set_paths()
    
    
    def set_paths(self):
            
        assert self.user in ["Josh", "Sabi", "Kevin", "Samudrika", "Leo", "Robert", "Main"], "Input a valid user name"
        assert self.system in ["windows", "Windows", "Linux", "linux"]

        if self.system == "windows" or self.system == "Windows":
            if self.user == "main" or self.user == "Main":
                onedrive = Path(f"C:\\FileSync\\adidas\\{self.onedrive_wd}\\projects_main")
            else:
                onedrive = Path(f"C:\\FileSync\\adidas\\{self.onedrive_wd}\\{self.user}")
                
        elif self.system == "linux" or self.system == "Linux":
            if self.user == "main" or self.user == "Main":
                onedrive = Path(f"/mnt/c/FileSync/adidas/{self.onedrive_wd}/projects_main")
            else:
                onedrive = Path(f"/mnt/c/FileSync/adidas/{self.onedrive_wd}/{self.user}")
            
        wd = onedrive / f"{self.project}"
        sql_dir = wd / "sql"
        functions_dir = wd / "functions"
        outputs_dir = wd / "output"
        data_dir = wd / "data"
        analysis_dir = wd / "analysis"
        pm_dir = wd / "project_management"
        dev_dir = wd / "development"
        
        dir_paths = {"working": wd,
                     "sql": sql_dir,
                     "functions": functions_dir,
                     "outputs": outputs_dir,
                     "data": data_dir,
                     "analysis": analysis_dir,
                     "project_management": pm_dir,
                     "development": dev_dir}

        return dir_paths
        
        
    def read_sql(self, SQL_query_file):
    
        """
        Returns a SQL query as a string from a file path to a .sql file.

        Parameters
        ----------
        
        SQL_query_path: str 
        
            Valid file path to a .sql file.
            
        Returns
        -------
            SQL Query as a string to be used with the execute_sql method.

        """
        
        file_name = f"{SQL_query_file}.sql"

        fd = open(self.paths["sql"] / file_name, 'r')
        SQL_query = fd.read()
        fd.close()

        return SQL_query


    def execute_sql(self, SQL_query, server=None, db=None, params=None, exasol=False):
        
        """
        Returns a Pandas data frame resulting from an input SQL query. Logic is such that 04 is the default 
        server. 

        Parameters
        ----------
           
        SQL_query: str 
            
            Valid SQL query, either entered manually or derived from read_sql method.
            
        server: str
            
            The name of a server for which an ODBC connection was set in __init__().
            
            Default is None, which connects to 04 PDX_SAP_USER.
        
        db: str
        
            A database to pull from. Should be a server for which in ODBC connection was set in __init__().
            
            Default is None, which connects to 04 PDX_SAP_USER.
        
        params: None or list
            
            SQL queries can be parameterized by adding ? character. Default is no parameters. 
            
            If params exists, must be passed as a list with parameter order corresponding to ? order.
            
        Returns
        -------
        
        A pd.DataFrame object.

        """

        if exasol == True:
            stmt = self.C.execute(SQL_query)
            return self.C.export_to_pandas(stmt.query)
        else:
            if server == None and db == None:
                cnxn = self.cnxns["USPORAMDB04_PDX_SAP_USER"]
                
            else:
                try:
                    # first try to connect using both inputs
                    cnxn = self.cnxns[f"{server.upper()}_{db.upper()}"]
                
                except:
                    # default to 04 if an error is thrown 
                    cnxn = self.cnxns[f"USPORAMDB04_{db.upper()}"]
                    
        
            try:
                return pd.read_sql(SQL_query, con=cnxn)
            
            except:
                return pd.read_sql(SQL_query, con=cnxn, params=params)
        
    
    def read_and_execute_sql(self, SQL_query_file, server=None, db=None, params=None, exasol=False):
        
        '''
        Read a .sql file to text and execute to return a Pandas dataframe. 
        
        Parameters
        ----------
        
        SQL_query_path: str 
        
            Name of a .sql file that exists in the sql folder of project directory. File extension can be 
            omitted. 
            
        server: str
            
            The name of a server for which an ODBC connection was set in __init__().
        
        db: str
        
            A database to pull from. Should be a server for which in ODBC connection was set in __init__().
            
        params: None or list
            
            SQL queries can be parameterized by adding ? character. Default is no parameters. 
            
            If params exists, must be passed as a list with parameter order corresponding to ? order.
            
        Returns
        -------
        
        A pd.DataFrame object.
        
        '''
        
        
        SQL_query = self.read_sql(self.paths["sql"] / f"{SQL_query_file}")

        if exasol == False: 
            try:
                return self.execute_sql(SQL_query=SQL_query, server=server, db=db)
            except:
                return self.execute_sql(SQL_query=SQL_query, server=server, db=db, params=params)

        else:
            stmt = self.C.execute(SQL_query)
            return self.C.export_to_pandas(stmt.query)
        
        
    def sql_version_check(self, base_sql_file_name):
        
        '''
        A helper function to search project's SQL folder for the most recent version of a SQL file. 
        Assumes versions are named with the following convention: base_sql_file_name_Vn where n is in [0, inf].
        
        Parameters
        ----------
        
        base_sql_file_name: str
            
            The base name of the versioned SQL file in your project's SQL folder. 
            
            e
        Returns
        -------
        
        The name of most recent version of the SQL file. Can be passed directly into read_and_execute_sql()
        '''
            
        #list all files in project sql directory that contain base_sql_file_name
        version_files = [os.path.split(x)[1] for x in glob.glob(str(self.paths["sql"] / f"{base_sql_file_name}*"))]

        # get versions of the base sql file
        versions = [int(x[x.find("V")+1]) for x in version_files if x.find("V") != -1]

        # return the most recent version 
        return f"{base_sql_file_name}_V{np.max(versions)}"
        
    
    
    def read_flat_file(self, file_name, folder="data",  extension=".csv", sheet=0, sep=",", 
                       dtype=None, parse_dates=False, header='infer'):

        '''
        
        Reads a .csv or .xlsx file to a Pandas dataframe.
        
        Parameters
        ----------
        
        file_name: str
            
            Name of the file to be read. File extension can be omitted. 
            
        folder_name: str
        
            Name of folder file is to be read from. Corresponds to a subdirectory of project folder.
            
            i.e. data, output, etc.
            
        extension: str
        
            File extension of file to be read. Should be ".csv" (Default) or ".xlsx". 
            
        sheet: int or str
            
            If reading an Excel file with multiple sheets, the sheet to be read.
            
            Not required for reading .csv files. 
            
            Default is first sheet in the file. Sheets can be specified by name or index.
            
            
        Returns
        -------
        
        A pd.DataFrame object.
        
        '''
    
        extensions = [".csv", ".xlsx", ".xls", ".txt", ".pkl"]
        
        assert extension in extensions, "Extension must be either .csv or .xlsx"
        
        file_path = self.paths[f"{folder}"] / file_name
        
        if extension == ".csv":
            if dtype is None:
                return pd.read_csv(f"{file_path}{extension}", sep=sep, parse_dates=parse_dates, header=header)
            else:
                return pd.read_csv(f"{file_path}{extension}", sep=sep, dtype=dtype, parse_dates=parse_dates, header=header)
            
        elif extension == ".xlsx" or extension == ".xls":
            if dtype is None:
                return pd.read_excel(f"{file_path}{extension}", sheet_name=sheet, header=header)
            else:
                return pd.read_excel(f"{file_path}{extension}", sheet_name=sheet, dtype=dtype, header=header)
                
        elif extension == ".txt":
            with open(f"{file_path}{extension}", 'r') as file:
                data = file.read() 
            return data
        
        elif extension == ".pkl":
            return pd.read_pickle(f"{file_path}{extension}")
                
    
    
    def save(self, files, file_names, folder="outputs", extension = ".csv", multi_sheet_excel=False, 
             sheet_names=None, quoting=None, float_format=None, index=False):
        
        """
        Saves a list of input files with specified file names.
        
        
        Parameters
        ----------
        
        files: pd.DataFrame or list 
        
            A list of input files to save.
            
        file_names: str or list 
        
            A list of file names where each file name corresponds to an input file.
            
        extension: str
        
            File extension to save files under. Should be ".csv" (default) or ".xlsx".
            
        multi_sheet_excel: bool
        
            Saves files inputs to a single Excel workbook with each file_name argument corresponding to the 
            name of a sheet.
            
            Input list as files, str as file names, and list as sheet_names to use.
            
        sheet_names: list
        
            List of sheet names to be input when using the multi sheet excel option. Not required otherwise.
            
        
        Returns
        -------
        
        None
        
        """
        
        if folder == "output":
            folder = "outputs"
        
        assert folder in ["data", "outputs", "project_management", "development"], "input valid output destination"
        
        files_dict = {}
        writer = None
        
        if multi_sheet_excel == True:
            extension = ".xlsx"
            writer = pd.ExcelWriter(self.paths[folder] / f"{file_names}{extension}", engine='xlsxwriter')

        if type(files) == list and type(file_names) == list:
            
            assert len(files) == len(file_names), "Each file must be associated with a file name"
            
            for i in range(len(files)):
                
                files_dict[file_names[i]] = files[i]
                
        elif isinstance(files, pd.DataFrame) and type(file_names) == str:
            
            files_dict[f"{file_names}"] = files
            
        elif type(files) == list and type(file_names) == str:
            
            writer = pd.ExcelWriter(self.paths[folder] / f"{file_names}{extension}", engine='xlsxwriter')
            
            assert sheet_names is not None, "Pass sheet names(list)"

            assert len(sheet_names) == len(files), "Files and sheet names must be same length"
            
            multi_sheet_excel=True
            
            sheets_dict = {}
            
            for i in range(len(files)):
                
                files_dict[sheet_names[i]] = " "
                
                sheets_dict[sheet_names[i]] = files[i]
                                                                 
        else:
            
            raise ValueError("files(pd.DataFrame or list), file_names(str or list)")
        
        
        for key in files_dict:
            
            if extension == ".xlsx":
                
                if not multi_sheet_excel:
                    files_dict[key].to_excel(self.paths[folder] / f"{key}{extension}")
                else:
                    sheets_dict[key].to_excel(writer, sheet_name=key, index=index)
            
            elif extension == ".csv":
                files_dict[key].to_csv(self.paths[folder] / f"{key}{extension}", quoting=quoting, float_format=float_format, index=index)
            
            elif extension == ".txt":
                files_dict[key].to_csv(self.paths[folder] / f"{key}{extension}", quoting=quoting, float_format=float_format)
            
            elif extension == ".pkl":
                files_dict[key].to_pickle(self.paths[folder] / f"{key}{extension}")
                
            else:
                raise ValueError("supported output formats: .csv, .xlsx, .txt, .pkl")
                
        
        if writer is not None:
            
            writer.save()
                        
        return
    
    
    def select_columns(self, df, selected_columns, selection_purpose):
        
        # Write in functionality for this so that it takes in a .csv you already have and adds another column to it.
        # Naming for output files is going to need changing, too.

        '''
        Extracts selected rows from a DataFrame and saves them to a .csv file for use later.

        df(pd.DataFrame): A Pandas DataFrame to extract row names from.
        selected_columns(list): A list of column names to be extracted from the input DataFrame.
        selection_purpose(str): The reason you want to select these particular columns.

        '''

        len_selected_columns = len(selected_columns)

        col_names = list(df.columns)
        nb_rows = len(col_names)

        cols_dict = {"All Columns": col_names, f"{selection_purpose}": []}

        for i in range(nb_rows):
            if i < len_selected_columns:
                idx = col_names.index(selected_columns[i])
                cols_dict[f"{selection_purpose}"].append(col_names[idx])
            else:
                cols_dict[f"{selection_purpose}"].append(np.nan)

        cols_df = pd.DataFrame.from_dict(cols_dict)
        
        cols_df.to_csv(self.paths["data"] / "Col_Names.csv")

        return cols_df
    
    
    def subset_by_colums(self, df, selection_purpose):
    
        '''
        Subset a Pandas DataFrame based on some selection purpose specified in a stored .csv file

        df(pd.DataFrame): A Pandas DataFrame to subset.
        path(str): path to a .csv file that contains information on selection purpose and columns to pull.
        selection_purpose(str): should match up with a column header in the .csv file specified by path arg.
        '''

        cols_needed = pd.read_csv(self.paths["data"] / "Col_Names.csv")[selection_purpose].dropna()
        

        return df[list(cols_needed)]
    
    
    @staticmethod
    def get_col_data_types(df):
        
        data_types = [df.iloc[:,i].apply(type).value_counts() for i in range(df.shape[1])]
        
        for data_type in data_types:
            print(data_type)
            print(" ")
            
    def group_stats(group):
        
        '''
        Extracts summary information from a pd.DataFrame that has had the .groupby method called.
        
        Parameters
        ----------
        
        group: pd.DataFrame
            
            A grouped pd.DataFrame object
            
            
        Returns
        -------
        Summary statistics (min, max, count, mean) for the grouped object passed.
        
        '''
        
        return {'min': group.min(), 'max': group.max(), 'count': group.count(), 'mean': group.mean()}
    
    
    @staticmethod
    def make_unequal_col_df(data, column_names):
    
        '''
        Converts lists of unequal length to a pd.DataFrame object by filling out the shorter lists with NaN.


        Parameters
        ----------

        data: list

            A nested list where each element is a list of data constituting a column.

        column_names: list

            A list of column names for the pd.DataFrame object.


        Returns
        -------

        A pd.DataFrame object.
        '''

        data_dict = {}

        max_column_length = np.max([len(column) for column in data])

        for column, column_name in zip(data, column_names):

            rows_to_add = max_column_length - len(column)

            extra_values = np.repeat(np.nan, rows_to_add)

            for value in extra_values:

                column.append(value)

            data_dict[column_name] = column

        # I have no idea why the df doesn't come out the canonical way but I had to write it with idx then transpose
        return pd.DataFrame(data, index=column_names).transpose()
    
    
    def format_columns(self, df, columns, ops):

        '''
        Formats Pandas DataFrame colummns based on a list of operations passed for a specific columns


        Parameters
        ----------

        df: A pd.DataFrame object.

            The Pandas dataframe containing columns that require reformatting.

        columns: str or list

            If only one column is to be formatted, a string is sufficient. Otherwise, pass a list of valid 
            column names. 

        ops: list or dict

            If formatting one column, pass a list of operations to be performed. If multiple columns, pass
            a dictionary where each element contains a list of operations.


        Returns
        -------

        A pd.DataFrame object.

        '''

        if type(columns) == str:
            assert type(ops) == list, "Pass correct combination of data types for columns and ops args"
            columns = [columns]

        if type(ops) == list:
            ops = {columns[0]: ops} 

        for column in columns:
            for i, op in enumerate(ops[column]):
                                
                assert op in ["to_numeric", "fill_na_0", "fill_na_0.0", "drop_na", "to_int32", "to_int64", 
                              "to_string", "fill_na_blank", "to_int_32_preserve_strings", 
                              "to_int_64_preserve_strings", "to_float", "to_float_preserve_strings",
                              "to_numeric_preserve_strings"], "Op error"

                if op == "to_numeric":
                    if i == 0:
                        s = pd.to_numeric(df[column], errors='coerce')
                    else:
                        s = pd.to_numeric(s, errors='coerce')
                        
                if op == "to_numeric_preserve_strings":
                    if i == 0:
                        s = df[column].apply(lambda x: self.to_numeric_preserve_strings(x))
                    else:
                        s = s.apply(lambda x: self.to_numeric_preserve_strings(x))
                        
                if op == "to_float":
                    if i == 0:
                        s = df[column].astype(np.foat64)
                    else:
                        s = s.astype(np.float64)
                        
                if op == "to_float_preserve_strings":
                    if i == 0:
                        s = df[column].apply(lambda x: self.to_float_preserve_strings(x))
                    else:
                        s = s.apply(lambda x: self.to_float_preserve_strings(x))

                elif op == "fill_na_0":
                    if i == 0:
                        s = df[column].fillna(0)
                    else:
                        s = s.fillna(0)

                elif op == "fill_na_0.0":
                    if i == 0:
                        s = df[column].fillna(0.0)
                    else:
                        s = s.fillna(0.0)
                        
                elif op == "fill_na_blank":
                    if i == 0:
                        s = df[column].fillna(" ")
                    else:
                        s = s.fillna(" ")

                elif op == "drop_na":
                    if i == 0:
                         s = df[column].dropna()
                    else:
                        s = s.dropna()

                elif op == "to_int32":
                    if i == 0:
                         s = df[column].astype(np.int32)
                    else:
                        s = s.astype(np.int32)
                        
                elif op == "to_int_32_preserve_strings":
                    if i == 0:
                        s = df[column].apply(lambda x: self.to_int32_preserve_strings(x))
                    else:
                        s = s.apply(lambda x: self.to_int32_preserve_strings(x))
                        
                elif op == "to_int_64_preserve_strings":
                    if i == 0:
                        s = df[column].apply(lambda x: self.to_int64_preserve_strings(x))
                    else:
                        s = s.apply(lambda x: self.to_int64_preserve_strings(x))

                elif op == "to_int64":
                    if i == 0:
                         s = df[column].astype(np.int64)
                    else:
                        s = s.astype(np.int64)

                elif op == "to_string":
                    if i == 0:
                         s = df[column].astype(str)
                    else:
                        s = s.astype(str)
                                                
            df[column] = s

        return df
    
    
    @staticmethod
    def to_numeric_preserve_strings(r):
        
        if type(r) == float or type(r) == int:
            return pd.to_numeric(r)
        
        elif type(r) == str:
            if any(c.isalpha() for c in r):
                return r
            else:
                return pd.to_numeric(r)
        else:
            return r
    
    
    @staticmethod
    def to_int64_preserve_strings(r):
        
        if type(r) in [float, np.float32, np.float64]:
            return np.int64(r)
        else:
            return r
        
        
    @staticmethod
    def to_int32_preserve_strings(r):
        
        if type(r) in [float, np.float32, np.float64]:
            return np.int32(r)
        else:
            return r
        
        
    @staticmethod
    def to_float_preserve_strings(r):
        
        if type(r) == int:
            return np.float64(r)

        else:
            return r


    @staticmethod
    def percent_diff(value1, value2):
    
        value_difference = np.absolute(value1 - value2)
        half_value_sum = (value1 + value2) / 2

        return value_difference / half_value_sum * 100
    
    



