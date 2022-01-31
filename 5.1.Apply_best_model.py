#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from sklearn import metrics
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score, accuracy_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
import datetime
from datetime import datetime
from datetime import timedelta
from datetime import date
import json
from google.cloud import storage
from google.oauth2 import service_account


# # Create table_current_year

# In[2]:


# Ignoring the warning related to Setting with copy.
pd.options.mode.chained_assignment = None

start_year = 2005

# Extract the current year
URL = 'https://www.resultados-futbol.com/ligue_1'
r = requests.get(URL)
page = r.content
soup = BeautifulSoup(page, 'html5lib')

current_year = int(soup.find('div', class_ = "titular-data").text.strip()[0:4])+1

# Define the countries and the years
Years = range(start_year,current_year + 1)

Countries = ['Portugal','Spain','England','Italy','Germany','France']


# In[3]:


# Create a dataframe with the extracted results of all teams for the 6 countries,
# for the current year


# Creation of an empty data frame for all teams in all countries
table_results_current_year = pd.DataFrame()

# Replace the name of the country by the name of the country/league in the
# resultados-futbol website
for Country in Countries:
    if Country == 'Portugal':
        country = 'portugal'
    elif Country == 'Spain':
        country = 'primera'
    elif Country == 'England':
        country = 'premier'
    elif Country == 'Italy':
        country = 'serie_a'
    elif Country == 'Germany':
        country = 'bundesliga'
    elif Country == 'France':
        country = 'ligue_1'
    else:
        print('Country not available, please choose between Portugal,    Spain, England, Italy, Germany or France')



    # Per each country:


    # Get the URLs of the teams
    URL = f'https://www.resultados-futbol.com/{country}'
    r = requests.get(URL)
    page = r.content
    soup = BeautifulSoup(page, 'html5lib')

    teams_URL_in_national_league = []

    for li in soup.find_all('li', class_ = "shield"):
        a = li.find('a', href=True)
        teams_URL_in_national_league.append(a['href'])


    # Creation of an empty data frame for all teams in one country, one year
    table_all_teams = pd.DataFrame()


    for team in teams_URL_in_national_league:

        URL = f'https://www.resultados-futbol.com/partidos/{team}'
        r = requests.get(URL)
        page = r.content
        soup = BeautifulSoup(page, 'html5lib')


        #  Get the name of the competitions of each team
        list_of_competitions = []

        for div in soup.find_all('div', class_ = "title"):
            img = div.find('img', alt=True)
            list_of_competitions.append(img['alt'])

        # Get the name of the team (not team URL)
        div_class_team = soup.find('div', class_ = "name")
        div_class_team_a = div_class_team.find('a')
        Team = div_class_team_a.get_text()

        # Some teams have a space in the end of the name, we need to
        # delete it
        if Team[-1] == ' ':
            Team = Team[:-1]
        else:
            Team = Team


        # Creation of an empty data frame for all results of one team
        table_team = pd.DataFrame()

        # Creation of data frame all the results of the team,
        # including a column with the name of the competition
        page = pd.read_html(URL)

        # The table with the first competition results is the table
        # that appears in position 5:
        for competition_i in range(5,5+len(list_of_competitions)):
            table_competition_i = pd.DataFrame(page[competition_i])
            table_competition_i['Competition_original_name_URL'] = list_of_competitions[competition_i-5]
            table_team = pd.concat(
                [table_team,table_competition_i],
             ignore_index = True, axis = 0)


        # Concat the table created for one team with the empty dataframe
        table_all_teams = pd.concat(
                [table_all_teams,
                 table_team],
            ignore_index = True, axis = 0)


    table_all_teams['Year'] = current_year


    # Concat the table created for one country with the empty dataframe
    table_results_current_year = pd.concat(
            [table_results_current_year,
             table_all_teams],
         ignore_index = True, axis = 0)


# # Create functions to manage the table

# In[4]:


def edit_raw_table(raw_table):


    # Drop duplicated games (the original table has all the games of all teams,
    # and as teams play against each other, many games are repeated).

    raw_table.drop_duplicates(inplace=True)

# Clean data, add columns, rename columns, reorder columns
    
    # Exclude all lines with NAs in column 2
    raw_table = raw_table[
        raw_table[2].notna()]
    
    # Exclude all columns with NA
    raw_table = raw_table.dropna(axis=1)
    
    # Rename columns
    raw_table.rename(columns = {1:'Date', 2:'Status', 3:'Home_team',
        4:'Result', 5:'Away_team'}, inplace = True)
    
    # Change the values of the match status
    raw_table['Status'] = raw_table['Status'].apply(
        lambda x: "Postponed" if "Aplazado" in x else \
            "Finalized" if "Finalizado" in x else \
            "Not played yet" if "en " in x else \
            "Still playing" if "'" in x else "Unknown")
    
    # Select only the columns we need
    raw_table = raw_table[[
        "Year","Date","Competition_original_name_URL",
        "Home_team","Away_team","Status","Result"]]

    
    # Create 2 columns with the goals of the home_team and away_team
    list_results = []
    
    for score in list(raw_table['Result']):
        if '-' in score:
            list_results.append(score)
        else:
            list_results.append('-')
    
    raw_table['Result'] = list_results
            
    list_home_score = []
    list_away_score = []
    
    for score in list(raw_table['Result']):
        if score == '-':
            list_home_score.append('-')
            list_away_score.append('-')
        elif '-' in score:
            list_home_score.append(score[:score.index('-')-1])
            list_away_score.append(score[score.index('-')+2:])
        else:
            list_home_score.append('-')
            list_away_score.append('-')
    
    raw_table['Home_score'] = list_home_score
    raw_table['Away_score'] = list_away_score
    
# Create a new column with the name of the country
    # First, we create lists with the names of the competitions per country
    raw_table['Country'] = list(raw_table['Competition_original_name_URL'])

    international_competition_list = ['Champions League', 'Europa League',
                                  'Copa Intercontinental', 'Copa Intertoto',
                                 'Mundial de Clubes', 'Supercopa Europa',
                                      'Previa Champions'
                                 ]

    portuguese_competitions = ['Liga Portuguesa', 
                               'Taça de Portugal', 
                               'Supercopa Portugal', 
                               'Copa de la Liga Portugal',
                              'Liga Portuguesa - Play Offs Ascenso']
    spanish_competitions = ['Primera División', 
                            'Copa del Rey', 
                            'Supercopa de España']
    english_competitions = ['Premier League', 
                            'FA Cup', 
                            'Community Shield', 
                            'EFL Cup']
    italian_competitions = ['Serie A', 
                            'Coppa Italia', 
                            'Supercopa de Italia']
    german_competitions = ['Bundesliga', 
                           'DFB Pokal', 
                           'Supercopa de Alemania', 
                           'Liga Pokal']
    french_competitions = ['Ligue 1', 
                           'Copa de Francia',  
                           'Supercopa Francia', 
                           'Copa de la Liga',
                          'Ligue 1 - Play Offs Ascenso']
    
    # Reset index before applying the following loop
    raw_table.reset_index(inplace = True)

    for i in range(len(list(raw_table['Country']))):
        if raw_table['Country'][i] in international_competition_list:
            raw_table['Country'][i] = 'International'
        elif raw_table['Country'][i] in portuguese_competitions:
            raw_table['Country'][i] = 'Portugal'
        elif raw_table['Country'][i] in spanish_competitions:
            raw_table['Country'][i] = 'Spain'
        elif raw_table['Country'][i] in english_competitions:
            raw_table['Country'][i] = 'England'
        elif raw_table['Country'][i] in italian_competitions:
            raw_table['Country'][i] = 'Italy'
        elif raw_table['Country'][i] in german_competitions:
            raw_table['Country'][i] = 'Germany'
        elif raw_table['Country'][i] in french_competitions:
            raw_table['Country'][i] = 'France'
        else:
            raw_table['Country'][i] = 'Friendly match'


    # Create dictionary to rename the competitions column

    competitions_initial_list = raw_table[
        'Competition_original_name_URL'].unique().tolist()

    dict_competitions = {}

    for initial_competition in competitions_initial_list:
        dict_competitions[initial_competition] = []

    for international_competition in international_competition_list:
        for initial_competition in competitions_initial_list:
            if international_competition in initial_competition:
                dict_competitions[initial_competition] = international_competition

    national_leagues_list = ['Bundesliga', 'Liga Portuguesa', 'Ligue 1',
                            'Premier League', 'Primera División', 'Serie A']

    for national_league in national_leagues_list:
        for initial_competition in competitions_initial_list:
            if national_league in initial_competition:
                dict_competitions[initial_competition] = 'National League'

    national_cups_list = ['Copa de Francia', 'Copa del Rey', 'Coppa Italia',
                            'FA Cup', 'DFB Pokal', 'Taça de Portugal']

    for national_cup in national_cups_list:
        for initial_competition in competitions_initial_list:
            if national_cup in initial_competition:
                dict_competitions[initial_competition] = 'National Cup'

    national_super_cup_list = ['Community Shield', 'Supercopa Francia', 'Supercopa Portugal',
                            'Supercopa de Alemania', 'Supercopa de Italia', 'Supercopa de España']

    for national_super_cup in national_super_cup_list:
        for initial_competition in competitions_initial_list:
            if national_super_cup in initial_competition:
                dict_competitions[initial_competition] = 'National Super Cup'

    national_leagues_cup_list = ['Copa de la Liga', 'EFL Cup', 'Liga Pokal']

    for national_leagues_cup in national_leagues_cup_list:
        for initial_competition in competitions_initial_list:
            if national_leagues_cup in initial_competition:
                dict_competitions[initial_competition] = 'National League Cup'
    
    # Convert the names of the remaining competitions in English
    
    dict_competitions['Trofeo Premier League Asia'] = 'Friendly match'            
    dict_competitions['Copa Intercontinental'] = 'Intercontinental Cup'
    dict_competitions['Copa Intertoto'] = 'Intertoto Cup'
    dict_competitions['Supercopa Europa'] = 'European Supercup'
    dict_competitions['Mundial de Clubes'] = 'Club World Cup'
    dict_competitions['Bundesliga - Play Offs Ascenso'] = 'Bundesliga Play Offs'
    dict_competitions['Liga Portuguesa - Play Offs Ascenso'] ='Liga Portuguesa Play Offs'
    dict_competitions['Ligue 1 - Play Offs Ascenso'] ='Ligue 1 Play Offs'

    # Still, there are competitions that have not been added to the dictionary:
    for competition in list(dict_competitions.keys()):
        if dict_competitions[competition] == 'Previa Champions':
            dict_competitions[competition] = 'Champions League'
    
    # For the ones that have not been added yet, we consider them as Friendly match
    for competition in list(dict_competitions.keys()):
        if dict_competitions[competition] == []:
            dict_competitions[competition] = 'Friendly match'


    # Add a column with the competition "standardized" name,
    # created with the dictionary above

    list_competition_standardized_name = []

    list_competition_original_name_URL = list(
        raw_table['Competition_original_name_URL'])

    for competition_original_name_URL in list_competition_original_name_URL:
        list_competition_standardized_name.append(
            dict_competitions[competition_original_name_URL])

    raw_table['Competition'] = list_competition_standardized_name

    raw_table = raw_table[
        ['Year', 'Country', 'Date',
            'Competition_original_name_URL', 'Competition', 'Home_team', 'Away_team', 
            'Status','Result', 'Home_score', 'Away_score']]
    
    
    # convert months in Spanish to months in English

    dict_months = {
        'Ene': 'Jan','Feb': 'Feb','Mar': 'Mar','Abr': 'Apr',
        'May': 'May','Jun': 'Jun','Jul': 'Jul','Ago': 'Aug',
        'Sep': 'Sep','Oct': 'Oct','Nov': 'Nov','Dic': 'Dec',
    }


    for i in range(len(list(raw_table['Date']))):
        month_es = raw_table['Date'][i][3:6]
        raw_table['Date'][i] = raw_table['Date'][i][0:3] +        dict_months[month_es] + raw_table['Date'][i][6:]
    

    # Create a new column with the date in the datetime format
    datetime_date_list = []

    for date in raw_table['Date']:
        date_object = datetime.strptime(date, "%d %b %y")
        datetime_date_list.append(date_object)
    
    raw_table.insert(list(raw_table.columns).index('Date')+1,'Datetime_date_list', datetime_date_list)
    
    
    # Drop results of non played games from previous seasons and reset index
    
    No_result = raw_table[(raw_table['Result'] == '-') &                          (raw_table['Year'] < current_year)
                         ].index
    raw_table.drop(No_result, inplace = True)
    raw_table.reset_index(inplace = True)


    # Add columns with 1x2 result and points for home and away team
    
    raw_table.loc[
        raw_table[
            'Home_score'] == raw_table['Away_score'], '1x2'] = 'x'
    raw_table.loc[
        raw_table[
            'Home_score'] > raw_table['Away_score'], '1x2'] = '1'
    raw_table.loc[
        raw_table[
            'Home_score'] < raw_table['Away_score'], '1x2'] = '2'
    
    raw_table['1x2'] = raw_table.apply(
    lambda row: row['1x2'] if row['Result'] != '-' else '-', axis=1)
    
    raw_table.loc[
        raw_table[
            '1x2'] == 'x', 'Points_Home_Team'] = int('1')
    raw_table.loc[
        raw_table[
            '1x2'] == '1', 'Points_Home_Team'] = int('3')
    raw_table.loc[
        raw_table[
            '1x2'] == '2', 'Points_Home_Team'] = int('0')
    raw_table.loc[
        raw_table[
            '1x2'] == 'x', 'Points_Away_Team'] = int('1')
    raw_table.loc[
        raw_table[
            '1x2'] == '1', 'Points_Away_Team'] = int('0')
    raw_table.loc[
        raw_table[
            '1x2'] == '2', 'Points_Away_Team'] = int('3')



    # Drop index column
    raw_table.drop(['index'], axis=1, inplace=True)
    
    return raw_table


# In[5]:


def fatigue(raw_table):

    # Calculate the number of games played by each team in the last days.
    last_days = 21


    # Create a new column with the number of games played by the home_team
    # in the last days, excluding friendly matches.
    number_of_games_last_days_home_team_list = []

    for i in range(raw_table.shape[0]):
        Team = raw_table['Home_team'][i]
        match_day = raw_table['Datetime_date_list'][i]
        match_day_minus_last_days = match_day - timedelta(days = last_days)

        number_of_games_last_days_home_team_list.append(
            sum(
        (raw_table.Datetime_date_list >= match_day_minus_last_days) & 
        (raw_table.Datetime_date_list < match_day) & 
        ((raw_table.Home_team == Team) | (raw_table.Away_team == Team)) & 
        (raw_table.Competition != 'Friendly match')
        )
        )

    raw_table['number_of_games_last_days_home_team'] = number_of_games_last_days_home_team_list

    # Create a new column with the number of games played by the away_team
    # in the last days, excluding friendly matches.
    number_of_games_last_days_away_team_list = []

    for i in range(raw_table.shape[0]):
        Team = raw_table['Away_team'][i]
        match_day = raw_table['Datetime_date_list'][i]
        match_day_minus_last_days = match_day - timedelta(days = last_days)

        number_of_games_last_days_away_team_list.append(
            sum(
        (raw_table.Datetime_date_list >= match_day_minus_last_days) & 
        (raw_table.Datetime_date_list < match_day) & 
        ((raw_table.Away_team == Team) | (raw_table.Home_team == Team)) & 
        (raw_table.Competition != 'Friendly match')
        )
        )

    raw_table['number_of_games_last_days_away_team'] = number_of_games_last_days_away_team_list

    # Note: teams outside the 6 national leagues will appear in international
    # games with 0 or very little games in the last days. However this is not
    # a problem, as we are not predicting game results of their national leagues,
    # nor international competitions.
    
    # Exclude all competitions which are not national leagues, which is the only type
    # of competition we will make predictions
    raw_table = raw_table[raw_table['Competition'] == 'National League']
    
    # Re-set index after having dropped many rows
    raw_table.reset_index(drop=True,inplace=True)
    
    return raw_table


# In[6]:


def points_respective_year_and_last_games(raw_table):
    
    # Calculate the number of points that each team has in the respective
    # season and also in the last games.
    
    n_last_games = 5
    
    # Create new columns that show the number of points of the home_team
    # and away_team
    
    number_of_points_respective_year_home_team_list = []
    number_of_points_last_games_home_team_list = []
    
    number_of_points_respective_year_away_team_list = []
    number_of_points_last_games_away_team_list = []
    
    
    for i in range(raw_table.shape[0]):
        
        # First, let's start with the points accumulated by the home_team
        # in the respective year and in the last games.

        home_team = raw_table.loc[i, 'Home_team']

        df_aux_respective_year_home_team = raw_table[((raw_table['Home_team'] == home_team) |            (raw_table['Away_team'] == home_team)) &            (raw_table['Year'] == raw_table.loc[i, 'Year']) &            (raw_table['Datetime_date_list'] < raw_table.loc[i, 'Datetime_date_list']) &            (raw_table['Competition'] == 'National League')
                          ]
        
        df_aux_last_games_home_team = df_aux_respective_year_home_team.sort_values(
            'Datetime_date_list')[-n_last_games:]
          
        if df_aux_last_games_home_team.shape[0] > 0:
            
            Points_respective_year_home_team =             (df_aux_respective_year_home_team[df_aux_respective_year_home_team['Home_team'] == home_team]             ['Points_Home_Team'].sum() +            df_aux_respective_year_home_team[df_aux_respective_year_home_team['Away_team'] == home_team]             ['Points_Away_Team'].sum())        
            
            Points_last_games_home_team =             (df_aux_last_games_home_team[df_aux_last_games_home_team['Home_team'] == home_team]             ['Points_Home_Team'].sum() +            df_aux_last_games_home_team[df_aux_last_games_home_team['Away_team'] == home_team]             ['Points_Away_Team'].sum())
        
        else:
            Points_respective_year_home_team = 0
            Points_last_games_home_team = 0
           
        number_of_points_respective_year_home_team_list.append(Points_respective_year_home_team)
        number_of_points_last_games_home_team_list.append(Points_last_games_home_team)
        
        
        # Now, let's calculate how many points the away_team has accumulated
        # in the respective year and in the last games
        
        away_team = raw_table.loc[i, 'Away_team']
        
        df_aux_respective_year_away_team = raw_table[((raw_table['Home_team'] == away_team) |            (raw_table['Away_team'] == away_team)) &            (raw_table['Year'] == raw_table.loc[i, 'Year']) &            (raw_table['Datetime_date_list'] < raw_table.loc[i, 'Datetime_date_list']) &            (raw_table['Competition'] == 'National League')
                                                 ]
                                                  
        df_aux_last_games_away_team = df_aux_respective_year_away_team.sort_values(
            'Datetime_date_list')[-n_last_games:]                             
                                                  
        if df_aux_last_games_away_team.shape[0] > 0:
            
            Points_respective_year_away_team =             (df_aux_respective_year_away_team[df_aux_respective_year_away_team['Home_team'] == away_team]             ['Points_Home_Team'].sum() +            df_aux_respective_year_away_team[df_aux_respective_year_away_team['Away_team'] == away_team]             ['Points_Away_Team'].sum())
            
            Points_last_games_away_team =             (df_aux_last_games_away_team[df_aux_last_games_away_team['Home_team'] == away_team]             ['Points_Home_Team'].sum() +            df_aux_last_games_away_team[df_aux_last_games_away_team['Away_team'] == away_team]             ['Points_Away_Team'].sum())
        
        else:
            Points_respective_year_away_team = 0
            Points_last_games_away_team = 0

        number_of_points_respective_year_away_team_list.append(Points_respective_year_away_team)
        number_of_points_last_games_away_team_list.append(Points_last_games_away_team)
        
    raw_table['points_respective_year_home_team'] = number_of_points_respective_year_home_team_list
    raw_table['points_respective_year_away_team'] = number_of_points_respective_year_away_team_list
    
    raw_table['points_last_games_home_team'] = number_of_points_last_games_home_team_list
    raw_table['points_last_games_away_team'] = number_of_points_last_games_away_team_list


    # We are only counting the points for the National League competitions,
    # as we are not predicting game results of other competitions.

    return raw_table


# In[7]:


def points_between_teams(raw_table):

    # Calculate the number of points that each team has got in the
    # same match in the previous years.

    
    # Create new columns that show the number of points of the home_team
    # and away_team for the same match in the previous years
    
    number_of_points_between_teams_home_team_list = []
    
    number_of_points_between_teams_away_team_list = []
    
    for i in range(raw_table.shape[0]):
        
        home_team = raw_table.loc[i, 'Home_team']
        away_team = raw_table.loc[i, 'Away_team']

        df_aux = raw_table[((raw_table['Home_team'] == home_team) &            (raw_table['Away_team'] == away_team)) &            (raw_table['Datetime_date_list'] < raw_table.loc[i, 'Datetime_date_list']) &            (raw_table['Competition'] == 'National League')
                          ]
        
        if df_aux.shape[0] > 0:
            
            Points_home_team =             df_aux[df_aux['Home_team'] == home_team]['Points_Home_Team'].sum()
            
            Points_away_team =             df_aux[df_aux['Away_team'] == away_team]['Points_Away_Team'].sum()
        
        else:
            Points_home_team = 0
            
            Points_away_team = 0
            
        number_of_points_between_teams_home_team_list.append(Points_home_team)
            
        number_of_points_between_teams_away_team_list.append(Points_away_team)
        
        
        
    raw_table['points_between_teams_home_team'] = number_of_points_between_teams_home_team_list
        
    raw_table['points_between_teams_away_team'] = number_of_points_between_teams_away_team_list


    # We are only counting the points for the National League competitions,
    # as we are not predicting game results of other competitions.

    return raw_table


# # Apply functions to table_current_year

# In[8]:


table_results_current_year = edit_raw_table(table_results_current_year)


# In[9]:


table_results_current_year = fatigue(table_results_current_year)


# In[10]:


table_results_current_year = points_respective_year_and_last_games(table_results_current_year)


# # Correct Team names of table_results_current_year

# In[11]:


table_results_previous_years = pd.read_excel('Table_results_previous_years_edited.xlsx')


# In[12]:


# Create 2 lists (one for previous years and another for the current year)
# with the unique names of the teams that have played the national leagues.

list_teams_previous_years = []
list1 = list_teams_previous_years

list_teams_current_year = []
list2 = list_teams_current_year


list1 = list(set(list(table_results_previous_years['Home_team']) +                 list(table_results_previous_years['Away_team'])))

list2 = list(set(list(table_results_current_year['Home_team']) +                 list(table_results_current_year['Away_team'])))

df_match = pd.DataFrame({'Name current year': list2})


# In[13]:


# Use the library fuzzywuzzy to match the names in both lists. The library
# gives us a score from 0 to 100: the higher the score, the more similar the
# names are. First I create a column with the name and the score of the 2
# top teams most similar, and then a second column only with the score of the
# most similar name.

df_match['Suggested from previous years'] = df_match['Name current year'].apply(
        (lambda x: process.extract(x, list1)[0:2])
    )

df_match['Suggested from previous years Score'] = df_match['Name current year'].apply(
        (lambda x: process.extractOne(x, list1)[1])
    )


# In[14]:


# The first 5 teams (Brentford, Clermont, Vizela, Venezia, Salernitana)
# are suggested names from other teams as they appear in the table for
# the first time in 2022 (it is their first appearence in the most important
# national league since the start year of this project). However, the
# following 6 teams are the ones with similar names in previous years.
# Those (and only those) are the names we need to correct.

# For Vitória and Olympique we get the same score for the 1st and 2nd suggestion.
# I've checked manually what is the right one.

table_results_current_year.loc[(
    table_results_current_year['Home_team'] == 'Brighton Hove Alb.'), 'Home_team'] = 'Brighton & Hove Albion'
table_results_current_year.loc[(
    table_results_current_year['Away_team'] == 'Brighton Hove Alb.'), 'Away_team'] = 'Brighton & Hove Albion'

table_results_current_year.loc[(
    table_results_current_year['Home_team'] == 'Vitória'), 'Home_team'] = 'Vitória Guimarães'
table_results_current_year.loc[(
    table_results_current_year['Away_team'] == 'Vitória'), 'Away_team'] = 'Vitória Guimarães'

table_results_current_year.loc[(
    table_results_current_year['Home_team'] == 'Olympique'), 'Home_team'] = 'Olympique Marseille'
table_results_current_year.loc[(
    table_results_current_year['Away_team'] == 'Olympique'), 'Away_team'] = 'Olympique Marseille'

table_results_current_year.loc[(
    table_results_current_year['Home_team'] == 'Eintracht'), 'Home_team'] = 'Eintracht Frankfurt'
table_results_current_year.loc[(
    table_results_current_year['Away_team'] == 'Eintracht'), 'Away_team'] = 'Eintracht Frankfurt'

table_results_current_year.loc[(
    table_results_current_year['Home_team'] == 'Mönchengladbach'), 'Home_team'] = 'B. Mönchengladbach'
table_results_current_year.loc[(
    table_results_current_year['Away_team'] == 'Mönchengladbach'), 'Away_team'] = 'B. Mönchengladbach'

table_results_current_year.loc[(
    table_results_current_year['Home_team'] == 'Paços Ferreira'), 'Home_team'] = 'Paços de Ferreira'
table_results_current_year.loc[(
    table_results_current_year['Away_team'] == 'Paços Ferreira'), 'Away_team'] = 'Paços de Ferreira'


# # Join Tables previous years and current year

# In[15]:


table_results_all_years = pd.concat(
            [table_results_previous_years,
             table_results_current_year],
         ignore_index = True, axis = 0)


# # Apply function points_between_teams

# In[16]:


table_results_all_years = points_between_teams(table_results_all_years)


# # Join the table with fifa data

# In[17]:


table_fifa_all_years = pd.read_excel('Table_fifa_all_years_edited.xlsx')


# #### Create dictionary to match team names

# In[18]:


# create a dictionary whose keys are the team names in the results table
# and the values are the possible names in FIFA for each one of those teams

d = {}

# Build 2 lists: one with unique values of all teams in results table and
# another with unique values of all teams in fifa table

for year in Years:
    for country in Countries:
        results_teams_list_year_country = list(set(
            list(table_results_all_years[(table_results_all_years['Year'] == year) & 
                     (table_results_all_years['Country'] == country)]
                     ['Home_team']) +\
            list(table_results_all_years[(table_results_all_years['Year'] == year) & 
                     (table_results_all_years['Country'] == country)]
                     ['Away_team'])))

        fifa_teams_list_year_country = list(set(
            list(table_fifa_all_years[(table_fifa_all_years['Year'] == year) & 
                     (table_fifa_all_years['Country'] == country)]
                     ['Name'])))
        
        print(year)
        print(country)
        print('\n')

        
# Code to find a possible mismatch between the number of teams per year and
# per country in the results and fifa tables (if data is accurate, it should
# not happen)
        
        
        if len(results_teams_list_year_country) != len(fifa_teams_list_year_country):
            print('********************************************************')
            print('********************************************************')
            print('********************************************************')
            print(f'ERROR: {year},{country},\n            Number of teams results table: {len(results_teams_list_year_country)},\n            Number of teams fifa table: {len(fifa_teams_list_year_country)}')
            print('********************************************************')
            print('********************************************************')
            print('********************************************************')
            print('\n')
        
        else:

            # We create an auxiliar DataFrame (df_aux) in order to sort the list of results
            # teams per year and per country by wuzzyfuzzy score, starting on the highest
            # score. This will allow to start matching names that have a higher level of
            # confidence, and consequently will allow to have a shorter list of names to
            # match the last teams, whose level of confidence is lower.
            
                
            data = {'Results_name':results_teams_list_year_country}
            df_aux = pd.DataFrame(data)
            
            df_aux['Fifa_name_suggested'] = df_aux['Results_name'].apply(
        (lambda x: process.extractOne(x, fifa_teams_list_year_country)[0])
    )
            
            df_aux['Fifa_name_suggested_fuzzywuzzy_score'] = df_aux['Results_name'].apply(
        (lambda x: process.extractOne(x, fifa_teams_list_year_country)[1])
    )
            
            df_aux.sort_values(by = ['Fifa_name_suggested_fuzzywuzzy_score'], ascending = False,
                          inplace = True)
            
            results_teams_list_year_country = list(df_aux['Results_name'])
            
  
            # Here we look for the best match between a results team name and a fifa team
            # name. For that we run different loops with different levels of fuzzywuzzy
            # score, starting in the highest one.
            
            
            fuzzywuzzy_score_level = [100,90,80,70,60,50,40,30,20,10,0]
            
            for results_team in results_teams_list_year_country:
                
                if results_team in d.keys():
                    continue
                
                else:

                    for score_level in fuzzywuzzy_score_level:

                        fuzzywuzzy_min_score = score_level

                        fifa_team_suggested = process.extractOne(results_team, 
                                fifa_teams_list_year_country)[0]
                        fifa_team_suggested_score = process.extractOne(results_team, 
                                fifa_teams_list_year_country)[1]

                        
                        # We remove the fifa_team_suggested from the list so the same name is
                        # not suggested twice
                        if fifa_team_suggested_score >= fuzzywuzzy_min_score:
                            fifa_teams_list_year_country.remove(fifa_team_suggested)

                            if fifa_team_suggested not in d.values():
                                
                                # With .loc we will create a dataframe just showing the rows in
                                # which the the team name is the fifa_team_suggested and then
                                # with .iloc we will get all the names of the team that appear
                                # in the fifa table
                                if results_team not in d.keys():
                                    d[results_team] = table_fifa_all_years.loc[
                                        table_fifa_all_years['Name']==fifa_team_suggested]\
                                    ['Fifa_team_all_names'].iloc[0]

                                else:
                                    d[results_team].append(
                                table_fifa_all_years.loc[table_fifa_all_years['Name']==fifa_team_suggested]
                                     ['Fifa_team_all_names'].iloc[0])

                            break


# In[19]:


# Manually correct the errors of the dictionary. These errors happen because one of the
# teams has a very different name in the results table compared to the fifa table, or
# because one team has an opponent team with a very similar name, so in these rare cases
# the library fuzzywuzzy does not work well.

d['Milan'] = table_fifa_all_years[table_fifa_all_years['Name']=='AC Milan']['Fifa_team_all_names'].iloc[0]
d['Inter'] = table_fifa_all_years[table_fifa_all_years['Name']=='Inter Milan']['Fifa_team_all_names'].iloc[0]
d['Fiorentina'] = table_fifa_all_years[table_fifa_all_years['Name']=='Firenze']['Fifa_team_all_names'].iloc[0]
d['Köln'] = table_fifa_all_years[table_fifa_all_years['Name']=='FC Cologne']['Fifa_team_all_names'].iloc[0]
d['Feirense'] = table_fifa_all_years[table_fifa_all_years['Name']=='F. Santa Maria da Feira']['Fifa_team_all_names'].iloc[0]
d['Saint-Étienne'] = table_fifa_all_years[table_fifa_all_years['Name']=='AS Saint-Etienne']['Fifa_team_all_names'].iloc[0]
d['PSG'] = table_fifa_all_years[table_fifa_all_years['Name']=='Paris Saint-Germain']['Fifa_team_all_names'].iloc[0]
d['Olympique'] = table_fifa_all_years[table_fifa_all_years['Name']=='Olympique de Marseille']['Fifa_team_all_names'].iloc[0]


# #### Join Results table and Fifa table

# In[20]:


# Add 2 auxiliar columns to table_results_all_years with all the fifa team names for both home
# and away team to help joining both tables

table_results_all_years['Home_team_fifa_team_all_names'] = table_results_all_years['Home_team'].apply(
        (lambda x: d[x])
    )

table_results_all_years['Away_team_fifa_team_all_names'] = table_results_all_years['Away_team'].apply(
        (lambda x: d[x])
    )


# In[21]:


# Join table_results_all_years and fifa table

# first we start adding to the results table the columns we need
# from the fifa table just for the home teams

df_join_only_home = pd.DataFrame()

Columns = ['ATT','MID','DEF','OVR','Rival_team','Budget_Mill_€']


for year in Years:
    for country in Countries:
        df_1 = table_results_all_years[(table_results_all_years['Year'] == year) &
                  (table_results_all_years['Country'] == country)
                  ]

        df_2 = table_fifa_all_years[(table_fifa_all_years['Year'] == year) &
                  (table_fifa_all_years['Country'] == country)
                  ]

        df_aux = pd.merge(df_1, df_2[['Fifa_team_all_names','ATT','MID','DEF',
                                      'OVR','Rival_team','Budget_Mill_€']], 
            left_on= 'Home_team_fifa_team_all_names', 
            right_on = 'Fifa_team_all_names')

        df_join_only_home = pd.concat([df_join_only_home,df_aux])



df_join_only_home.drop(['Fifa_team_all_names'], axis=1, inplace=True)

# Here we rename the new columns and add "Home_team" as a prefix
for column in Columns:
    df_join_only_home.rename({
    column:f'Home_team_{column}'
    }, axis=1, inplace=True)


# Now that we have added the home team data, let's add it for the away team.
# Here one of the tables to merge is the one we had generated for the
# home_team
    
df_join_total = pd.DataFrame()

for year in Years:
    for country in Countries:
        df_1 = df_join_only_home[(df_join_only_home['Year'] == year) &
                  (df_join_only_home['Country'] == country)
                  ]

        df_2 = table_fifa_all_years[(table_fifa_all_years['Year'] == year) &
                  (table_fifa_all_years['Country'] == country)
                  ]

        df_aux = pd.merge(df_1, df_2[['Fifa_team_all_names','ATT','MID','DEF',
                                      'OVR','Rival_team','Budget_Mill_€']], 
            left_on= 'Away_team_fifa_team_all_names', 
            right_on = 'Fifa_team_all_names')

        df_join_total = pd.concat([df_join_total,df_aux])


df_join_total.drop(['Fifa_team_all_names'], axis=1, inplace=True)

# Here we rename the new columns and add "Away_team" as a prefix
for column in Columns:
    df_join_total.rename({
    column:f'Away_team_{column}'
    }, axis=1, inplace=True)


# In[22]:


# In order to simply the code from now on, and considering we
# already have all the info we need in just 1 table, let's call
# simply df to the new data frame

df = df_join_total


# #### New column: Rivals

# In[23]:


# Let's add another column that tells us if the game between the 2 teams
# is between rivals. If they are, the column will show 1, otherwise it
# will show 0.

df['Rivals'] = df.apply(
lambda x: 1 if (x['Home_team'] == x['Away_team_Rival_team'] or x['Away_team'] == x['Home_team_Rival_team']) else 0, axis = 1
)

# Let's drop some irrelevant columns from the df

df.drop(['Datetime_date_list','Competition_original_name_URL',
    'Home_score', 'Away_score',
    'Points_Home_Team', 'Points_Away_Team',
    'Home_team_fifa_team_all_names',
    'Away_team_fifa_team_all_names'], axis = 1, inplace = True)


# # Read df as the dataframe with all info (table_results + fifa, all years)

# # Let's train the model

# In[24]:


# Let's extract the games of the current weekday and the ones of the following one

current_weekday_matches = []
following_weekday_matches = []

for Country in Countries:

    if Country == 'Portugal':
        country = 'portugal'
    elif Country == 'Spain':
        country = 'primera'
    elif Country == 'England':
        country = 'premier'
    elif Country == 'Italy':
        country = 'serie_a'
    elif Country == 'Germany':
        country = 'bundesliga'
    elif Country == 'France':
        country = 'ligue_1'
    else:
        print('Country not available, please choose between Portugal,    Spain, England, Italy, Germany or France')


    # Current weekday matches (the current weekday is the one that opens by
    # default when we open the page of the respective league in the "resultados
    # futbol" website).

    URL = f'https://www.resultados-futbol.com/{country}'
    r = requests.get(URL)
    page = r.content
    soup = BeautifulSoup(page, 'html5lib')
    for match_ in range(len(soup.find_all(class_ = "summary hidden"))):
        match = soup.find_all(class_ = "summary hidden")[match_].text
        current_weekday_matches.append(match)
    
    
    current_weekday = soup.find_all('div', class_ = "j_cur")[1].find('a').text
    current_weekday_number = int(re.findall(r'\d+', current_weekday)[0])
    following_weekday_number = current_weekday_number+1
    
    # Following weekday matches

    URL = f'https://www.resultados-futbol.com/{country}/grupo1/{following_weekday_number}'
    r = requests.get(URL)
    page = r.content
    soup = BeautifulSoup(page, 'html5lib')
    for match_ in range(len(soup.find_all(class_ = "summary hidden"))):
        match = soup.find_all(class_ = "summary hidden")[match_].text
        following_weekday_matches.append(match)


# In[25]:


# Add a column with the type of weekday (current, following, other)

df['Weekday'] = df.apply(
lambda row: 'Current' if ((row['Year'] == current_year) and \
    ((row['Home_team'] + ' - ' + row['Away_team']) in current_weekday_matches)) \
    else 'Following' if ((row['Year'] == current_year) and \
    ((row['Home_team'] + ' - ' + row['Away_team']) in following_weekday_matches)) \
    else 'Other', axis=1)


# In[26]:


# The train dataset is all the dataset with finalized games

df_train = df[df['Status'] == 'Finalized']


# In[27]:


# The columns we use to train the algorithm are the ones we have selected in the 
# previous notebook, when we were looking for the best model.

X_train = df_train[['Year', 'Country', 'Home_team', 'Away_team',
       'number_of_games_last_days_home_team', 'number_of_games_last_days_away_team',
       'points_respective_year_home_team', 'points_respective_year_away_team',
       'points_last_games_home_team', 'points_last_games_away_team',
       'points_between_teams_home_team', 'points_between_teams_away_team',
       'Home_team_OVR', 'Away_team_OVR', 'Rivals']]

y_train = df_train['1x2']


# In[28]:


# Although the columns "Year" and "Rivals" are of type integer, they are basically
# "tags" and should be considered as text, because its values being higher or lower
# should not be considered better or worse, unlike the other columns of type integer.

X_train_numeric_data = X_train.select_dtypes(include=['int64', 'float64']
                ).drop(['Year','Rivals'],axis=1)

X_train_categorical_data = X_train[list(X_train.select_dtypes(include=['object']).columns) +                                      ['Year','Rivals']]


# In[29]:


# Let's create a dataframe with only the games we need to predict.

df_predictions = df[(df['Year'] == current_year) &                    (df['Weekday'] != 'Other')]


# In[30]:


# We just need the columns that are used in the train set.

X_predict = df_predictions[['Year', 'Country', 'Home_team', 'Away_team',
       'number_of_games_last_days_home_team', 'number_of_games_last_days_away_team',
       'points_respective_year_home_team', 'points_respective_year_away_team',
       'points_last_games_home_team', 'points_last_games_away_team',
       'points_between_teams_home_team', 'points_between_teams_away_team',
       'Home_team_OVR', 'Away_team_OVR', 'Rivals']]
y_predict = df_predictions['1x2']


# In[31]:


# Again, let's consider the columns "Year" and "Rivals" as categorical and not
# numeric.

numeric_columns = X_predict.select_dtypes(include=['int64', 'float64']
        ).drop(['Year','Rivals'],axis=1).columns

categorical_columns = list(X_predict.select_dtypes(include=['object']).columns) + ['Year','Rivals']


# In[32]:


# We will apply here the same pipeline we used when finding the best
# model. It consists in applying the transformer Standard Scaler to
# the numeric columns and OneHotEncoder to the categorical ones.
# Then, apply the best model (LogisticRegression) with the best
# parameters (C=10)

numeric_transformer = Pipeline(steps=[
    ('scaler', StandardScaler())])

categorical_transformer = Pipeline(steps=[
    ('onehot', OneHotEncoder(handle_unknown='ignore'))])

preprocessor = ColumnTransformer(
    transformers=[
        ('num', numeric_transformer, numeric_columns),
        ('cat', categorical_transformer, categorical_columns)])

model = Pipeline(steps=[
    ('preprocessor', preprocessor),
    ('model', LogisticRegression(C=10))])

model.fit(X_train, y_train)
y_pred = model.predict(X_predict)


# In[33]:


# Finally, let's build a DataFrame with the info we want to show the final user:
# basic info about the game (Year, Country, Weekday, Date, Status, Home_team,
# Away_team and result - for the games that have already finished) and what is
# the prediction of the result (and the probability of each outcome).

list_predictions = []

for i in range(df_predictions.shape[0]):
    list_predictions.append(y_pred[i])


list_probability_1 = []
list_probability_2 = []
list_probability_X = []

for i in range(df_predictions.shape[0]):
    probability_1_i = model.predict_proba(X_predict[i:i+1]).tolist()[0][0]
    probability_1_i = str(round(probability_1_i*100,1)) + '%'
    list_probability_1.append(probability_1_i)

    probability_2_i = model.predict_proba(X_predict[i:i+1]).tolist()[0][1]
    probability_2_i = str(round(probability_2_i*100,1)) + '%'
    list_probability_2.append(probability_2_i)
    
    probability_X_i = model.predict_proba(X_predict[i:i+1]).tolist()[0][2]
    probability_X_i = str(round(probability_X_i*100,1)) + '%'
    list_probability_X.append(probability_X_i)

    
# Let's create the dataframe final_user with the columns predictions and
# probability of each match outcome

df_final_user = df_predictions.copy()
    
df_final_user['Prediction'] = list_predictions
df_final_user['Probability 1'] = list_probability_1
df_final_user['Probability X'] = list_probability_X
df_final_user['Probability 2'] = list_probability_2

# Let's also delete the underscore from the column names Home_team and
# Away_team, so those names look better when showing them to the final user

df_final_user.rename(columns={'Home_team':'Home team','Away_team':'Away team'},
                    inplace=True)

df_final_user = df_final_user[['Year','Country','Weekday','Date',
'Status','Home team','Away team','Result','Prediction', 'Probability 1',
'Probability X', 'Probability 2']]


# In[34]:


# Create a column with the date of the last udpate. This will be used
# to show the user when was the table updated for the last time.

last_update_date = date.today().strftime("%d %b %Y")

df_final_user['Last update date'] = last_update_date


# In[35]:


# Let's order matches by date. For taht we need to create a new column
# with the date in a format that python can understand. Then we can
# drop that column,as it does not show value to the user.

datetime_date_list = []

for date in df_final_user['Date']:
    date_object = datetime.strptime(date, "%d %b %y")
    datetime_date_list.append(date_object)
    
df_final_user['Datetime_date_list'] = datetime_date_list

df_final_user.sort_values('Datetime_date_list',inplace=True)

df_final_user.drop('Datetime_date_list',axis=1,inplace=True)


# In[36]:


# Now let's save the dataframe to the Google Cloud Storage Bucket

# First we save it to the local machine
df_final_user.to_csv('Table_final_user.csv', index=False)

# Then, we establish connection to the bucket in Google Cloud Storage service.
# For this, I created first a service account key and have downloaded it to
# my local machine. After that, I read the file in order to access the bucket.
path_to_token = 'service_account_key_tfm.json'
storage_credentials = service_account.Credentials.from_service_account_file(path_to_token)
storage_client = storage.Client(project='tiago-project', credentials = storage_credentials)
destination_bucket = storage_client.bucket('tiago-tfm-kschool')

# Once I have access to the bucket, I can upload there the CSV with the dataframe.
# This dataframe will later be read by the streamlit app I have created in order to
# show the user the predictions of the results.
blob = destination_bucket.blob('Table_final_user.csv')
blob.upload_from_filename('Table_final_user.csv')

