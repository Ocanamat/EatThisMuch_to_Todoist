import os
import re
import yaml
import pickle 
import todoist
import dateutil.parser as dp
import pprint
import pandas as pd

from bs4.builder import TreeBuilder
from datetime import date, datetime
from bs4 import BeautifulSoup

#from markdownify import markdownify
#import json
#import string
#import tempfile
#import sys


appdir = os.path.dirname(os.path.realpath(__file__))  # rp, realpath
datadir = os.path.join(appdir, "data")

# Check datadir exists
if not os.path.exists(datadir):
    os.makedirs(datadir)

# Read config
with open(os.path.join(appdir, 'config.yaml'), 'r') as f:
    config = yaml.load(f.read(), Loader=yaml.FullLoader)

# Fetch todoist items
api = todoist.TodoistAPI(config['todoist_token'])
api.sync()

# Define mealplan files
weekplan_html_path = os.path.abspath(config['etm_html_filepath'])


if config['debug']:
    with open(os.path.join(appdir, "debug.json"), "w+", encoding="utf-8") as f:
        f.write(pprint.pformat(api.state, indent=4))


def debug(text):
    if config['debug']:
        print(text)


def parse_mealplan(weekplan_html_path):
    """
    parse_mealplan parses the local ETM HTML and returns a dataframe of the current week mealplan.

    :return: dataframe consisting of
        rows: Mealplan for a given date
        cols:   
            date: Mealplan date
            task: meal type (Bfast, Lunch, Dinner, Snack)
            meals: list of meals for given meal type
            links: list of links to recipe / description of meals
    """ 

    soup = BeautifulSoup(open(weekplan_html_path, encoding='utf8'), 'html.parser')
    mealplan_df =  pd.DataFrame({   'date':[], 
                                    'task':[], 
                                    'comment':[]}, 
                                    dtype = 'object')
    cols = list(mealplan_df)                                  

    # Table
    #main_table =  soup.find_all('div', attrs = {'class': 'plain-table'}, recursive = False)
    main_table =  soup.find('div', attrs = {'class': 'plain-table'})

    # Section
    for section in main_table.find_all('div', attrs = {'class': 'keep-together'}):

        # Dates
        date = section.find('th', attrs = {'class': 'small-12 ns table-sub-title td-w-30 small-bold small-larger-text'}).get_text().strip()
        
        # Meals
        for meal_sp in section.find_all('th', attrs = {'class': 'small-12 vertical-top t-w-50 small-extra-padding'}):
            # Meal title
            meal_title = meal_sp.find('td', attrs = {'class': 'table-block-title small-extra-padding'}).get_text().strip().replace("\xa0\n", "")
            pattern = re.compile(r'(.)\1{5,}')
            meal_title = re.sub(pattern, ' ', meal_title)
            #print(meal_title)
            meal_title = meal_title.replace("\n", "")

            # Meal Name
            meal = [meal.text.strip() for meal in meal_sp.find_all('a', href = re.compile("^#directions-") )]
            sep = ', '
            meal = sep.join(meal)
            #link = [link.get('href') for link in meal_sp.find_all('a')

            # DF Out
            #mealplan_df.append(dict(zip(cols, [date, meal_title, meal])), ignore_index=True)
            mealplan_df.loc[len(mealplan_df)] = [date, meal_title, meal]

            # Meal Link    
            #meals.append(meal)
            #links.append(link)

        # Second part of daily meal (included in a different type of tag)
        #dinner_sp = section.find_next_sibling('table')
        #meal_title = dinner_sp.find('td', attrs = {'class': 'table-block-title small-extra-padding'}).get_text().strip().replace("\xa0\n", "")
        #pattern = re.compile(r'(.)\1{5,}')
        #meal_title = re.sub(pattern, ' ', meal_title)
        #meal_title = meal_title.replace("\n", "")

        # Meal Name
        #meal = [meal.text.strip() for meal in dinner_sp.find_all('a', href = re.compile("^#directions-") )]
        
        #mealplan_df.loc[len(mealplan_df)] = [date, meal_title, meal]

        # Other Development
        ## Finding and extracting recipes
        #recp_table = soup.find_all('a', attrs = {'id': re.compile("directions")})
        #recp_table = soup.select("div.div.table.plain-table")
        #len(recp_table)
        #temp = recp_table[0].parent.parent.parent.get_text('\n')


    return mealplan_df


#def parse_mealplan_downloaded():
    """
    parse_mealplan parses the local ETM HTML that has been manually downloaded from ETM dashboard and returns a dataframe of the current week mealplan.

    :return: dataframe consisting of
        rows: Mealplan for a given date
        cols:   
            date: Mealplan date
            task: generic string for todoist
            breakfast: list of breakfast meals
            bfast_link: link to meal recipe
            lunch: list of lunch meals
            lunch_link: link to meal recipe
            dinner: list of dinner meals
            dinner_link: link to meal recipe
    """ 
    mealplan_df =  pd.DataFrame({   'date':[], 
                                    'task':[], 
                                    'comment':[]})

    n_sect = 0
    for section in soup.find_all('div', attrs = {'class': 'keep-together'}):
        if section.find(class_='meal-plan-title-row'):
            link = [link.get('name') for link in section.find_all('a')][0]
            date = dp.parse(link.replace('plan', ''))
            #print(date)
        
        else:
            
            n_subsect = 0
            layout = [layout.text for layout in section.find_all('p', attrs = {'class': 'meal-title text-left'} )]
            print(n_sect, layout, '<-----------' )

            meals = []
            links = []

            for subsection in section.find_all('table', attrs = {'class': 'row keep-together'}):
                meal = [meal.text for meal in subsection.find_all('h4')]
                link = [link.get('href') for link in subsection.find_all('a')]
                
                meals.append(meal)
                links.append(link)

                #print(n_subsect, meal, link)

                n_subsect += 1


            mealplan_df[n_sect + n_subsect, 'date'] = date
            mealplan_df[n_sect + n_subsect, 'task'] = link.replace('plan', '') + 'Meals'
            mealplan_df[n_sect + n_subsect, 'task'] = link.replace('plan', '') + 'Meals'
            
            n_sect += 1
    
    return mealplan_df


def get_last_mealplan_path(data_path):
    files = [x for x in os.listdir(data_path)]
    newest = max(files) # , key = os.path.getctime)
    #print "Recently modified Docs",newest
    return data_path + "\\" + newest


def get_last_mealplan(lastweekplan_data_path):
    saved_items = []
    saved_items_file = open(lastweekplan_data_path, "rb")

    while 1:
        try:
            saved_items.append(pickle.load(saved_items_file))
        except EOFError:
            break
    saved_items_file.close()
    
    return saved_items


# Todoist API
# Items' fields: content, description, due, has_more_notes, id, checked, priority    
# items.add (content, project_id, date_string, description, due, parent_id)

# Sample Todoist Upload
# import todoist >>> 
# api = todoist.TodoistAPI('0123456789abcdef0123456789abcdef01234567') >>> 
# item = api.items.add('My taks')  # oh no, typo! >>> 
# api.commit()  
#  commit the changes to the server {'id': 1234567890, u'content': u'My taks', u'user_id': 1, ...} 
# api.items.update(item['id'], content='My task') >>> 
# api.commit()  
#   never forget to commit! {'id': 1234567890, u'content': u'My task', u'user_id': 1, ...} ` 


def upload_day_mealplan(task,content,date):
    """
    add_day_mealplan uploads a task with its given date to todoist and records the uID of the task.
    
    """ 
    item = api.items.add(content = task, description = content, due = {'string': date})
    api.commit()

    return item



# if config['clean_up_completed_tasks']:
# print(f"Deleting task '{item['content']}'")
# task = api.items.get_by_id(item['id'])
# task.delete()
# api.commit()


if __name__ == "__main__":
    # TODO Parse recipe links
    # TODO Send recipe links to todoist comments
    # TODO Add notifications of what the program is doing to command line

    local_filepath = os.path.join(appdir, config['filename_output'])

    # 1. Check ETM HTML Exists
    if not os.path.exists(weekplan_html_path):
        print('Missing ETM HTML File') 


    # 2. Parse ETM HTML
    mealplan = parse_mealplan(weekplan_html_path)


    # 3. Rename ETM HTML
    meals_directory = os.path.dirname(weekplan_html_path)
    os.rename(weekplan_html_path, meals_directory + '\\' + datetime.now().strftime("%Y%m%d") + "_Week_Mealplan.html")
    

    # 4. Check if logged ETM tasks exists
    #       - TRUE: Mark undone logged tasks as done / and delete
    #       - FALSE: Print no tasks needed to be updated
    lastweekplan_data_path = get_last_mealplan_path(datadir)
    lastweek_tasks = get_last_mealplan(lastweekplan_data_path)
    if not lastweek_tasks:
        print('No meal plans have been updated in Todoist')
    else:
        for item in lastweek_tasks:                        
            item_dic = dict(item.data)
            item_delete = api.items.get_by_id(item_dic['id'])
            try:
                item_delete.delete()
                api.commit()
            except AttributeError:
                continue

            
    # 5. Load ETM Meals as tasks
    # 6. Save ETM tasks' items to local pickle file
    weekplan_data_path = os.path.join(datadir, datetime.now().strftime("%Y_%m_%d") + "_ETM_data.pickle")
    weekplan_data_path_fh = open(weekplan_data_path, "wb")
    for i, mealtask in mealplan.iterrows():
        task = mealtask['task']
        content = mealtask['comment']
        date = mealtask['date']
        uploaded_task = upload_day_mealplan(task, content, date)
        
        pickle.dump(uploaded_task, weekplan_data_path_fh)
        #print(uploaded_task)
    weekplan_data_path_fh.close()
        
  