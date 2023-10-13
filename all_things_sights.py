import openai
import re
import pandas as pd
import time
import json
import requests
import base64
import os
from PIL import Image
from io import BytesIO
from openai.error import APIError, RateLimitError
import random
import folium
import wikipediaapi
from openai.error import InvalidRequestError

openai.api_key = "###"
#länder cluster
afrika = [
    "Algerien", "Angola", "Benin", "Botswana", "Burkina Faso", "Burundi",
    "Cabo Verde", "Kamerun", "Zentralafrikanische Republik", "Tschad",
    "Komoren", "Kongo", "Dschibuti", "Ägypten", "Äquatorialguinea", "Eritrea",
    "Eswatini", "Äthiopien", "Gabun", "Gambia", "Ghana", "Guinea", "Guinea-Bissau",
    "Elfenbeinküste", "Kenia", "Lesotho", "Liberia", "Libyen", "Madagaskar",
    "Malawi", "Mali", "Mauretanien", "Mauritius", "Mosambik", "Namibia",
    "Niger", "Nigeria", "Ruanda", "São Tomé und Príncipe", "Senegal", "Seychellen",
    "Sierra Leone", "Somalia", "Südafrika", "Südsudan", "Tansania", "Togo", "Uganda",
    "Sambia", "Simbabwe"
]

asien = [
    "Afghanistan", "Armenien", "Aserbaidschan", "Bahrain", "Bangladesch", "Bhutan",
    "Brunei", "Kambodscha", "China", "Osttimor", "Georgien", "Indien", "Indonesien",
    "Iran", "Irak", "Israel", "Japan", "Jordanien", "Kasachstan", "Kuwait", "Kirgisistan",
    "Laos", "Libanon", "Malaysia", "Malediven", "Mongolei", "Myanmar", "Nepal", "Oman", 
    "Pakistan", "Palau", "Philippinen", "Katar", "Saudi-Arabien", "Singapur",
    "Südkorea", "Sri Lanka", "Syrien", "Tadschikistan", "Thailand", "Türkei",
    "Turkmenistan", "Usbekistan", "Vereinigte Arabische Emirate", "Vietnam", "Jemen"
]

europa = [
    "Albanien", "Andorra", "Österreich", "Belarus", "Belgien", "Bosnien und Herzegowina",
    "Bulgarien", "Kroatien", "Zypern", "Tschechien", "Dänemark", "Estland", "Finnland",
    "Frankreich", "Deutschland", "Griechenland", "Ungarn", "Island", "Irland", "Italien",
    "Kosovo", "Lettland", "Liechtenstein", "Litauen", "Luxemburg", "Malta", "Moldawien",
    "Monaco", "Montenegro", "Niederlande", "Mazedonien", "Norwegen", "Polen", "Portugal",
    "Rumänien", "Russland", "San Marino", "Serbien", "Slowakei", "Slowenien", "Spanien",
    "Schweden", "Schweiz", "Ukraine", "England", "Vatikanstadt"
]

nordamerika = ["Anguilla", "Antigua und Barbuda", "Aruba", "Bahamas", "Barbados",
    "Belize", "Bermuda", "Britische Jungferninseln", "Kaimaninseln", "Costa Rica", "Kuba",
    "Curaçao", "Dominica", "Dominikanische Republik", "El Salvador", "Grenada", "Guadeloupe",
    "Guatemala", "Haiti", "Honduras", "Jamaika", "Martinique", "Montserrat", "Niederländische Antillen",
    "Nicaragua", "Panama", "Puerto Rico", "St. Kitts und Nevis", "St. Lucia", "St. Vincent und die Grenadinen",
    "Trinidad und Tobago", "Turks- und Caicosinseln", "Vereinigte Staaten", "Virgin Islands (US)"
]

suedamerika = [
    "Argentinien", "Bolivien", "Brasilien", "Chile", "Kolumbien", "Ecuador", "Guyana", "Paraguay",
    "Peru", "Surinam", "Uruguay", "Venezuela"
]

ozeanien = [
    "Australien", "Fidschi", "Französisch-Polynesien", "Kiribati", "Marshallinseln", "Mikronesien",
    "Nauru", "Neuseeland", "Palau", "Papua-Neuguinea", "Samoa", "Tonga", "Tuvalu", "Vanuatu"
]

kontinente = {
    "Afrika",
    "Asien",
    "Europa",
    "Nordamerika",
    "Südamerika",
    "Ozeanien"
}


# RELEVENT VARIABLES
n_start = 8
n_end = 15
category_id = "###"

country_list = "###"
country_name = "###"
zoom_level = 12 #maximal herangezoomed ist: 18, maximal herausgezoomed ist: 1 - Länder waren auf 4, Städte und Regionen auf 12


lang = "deutsch"


#Picture Sizes
header_pic_size = "1024x1024"
content_pic_size = "256x256"

# WORD PRESS VARIABLES 
wordpress_user = "###"
wordpress_password = "###"
wordpress_credentials = wordpress_user + ":" + wordpress_password
wordpress_token = base64.b64encode(wordpress_credentials.encode())
wordpress_header = {'Authorization': 'Basic ' + wordpress_token.decode('utf-8')}
# v hier weden bilder runtergeladen v
folder_path = '###'



################################################################################################
#FUNCTIONS
#### OPEN AI
def openAI_content(system_act_as, user_prompt):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_act_as},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.5
    )
    prompt_tokens = response["usage"]["prompt_tokens"]
    completion_tokens = response["usage"]["completion_tokens"]
    cost_prompt = prompt_tokens * (0.03/1000)
    cost_completion = completion_tokens * (0.06/1000)
    total_cost = cost_prompt + cost_completion
    total_cost = round(total_cost, 3)

    generated_content = response.choices[0].message.content

    return generated_content, total_cost


def openAI_picture(header_size, user_prompt):
    try:
        response = openai.Image.create(
            prompt=user_prompt,
            n=1,
            size=header_size
        )
        url = response['data'][0]['url']
        
        if header_size == "1024x1024":
            total_cost = 0.020
        elif header_size == "512x512":
            total_cost = 0.018
        else:
            total_cost = 0.016
        
        return url, total_cost
    
    except InvalidRequestError:
        return None, None


#########
### WORDPRESS FUNCTIONS BELOW
####################
def create_wordpress_category(title_tag, description_tag, slug):
    api_url = "###/wp-json/wp/v2/categories"
    data = {
        "name": title_tag,
        "description": description_tag,
        "slug": slug
    }
    response = requests.post(api_url,headers=wordpress_header, json=data)
    print(response)
    
def create_wordpress_post(title, slug, content, excerpt, category, featured_media):
    api_url = '###/wp-json/wp/v2/posts'
    data = {'title' : title, 
            'status': 'publish',
            'slug' : slug,
            'content': content,
            "excerpt": excerpt,
            "comment_status": "closed",
            "ping_status": "closed",
            "categories": category,
            "featured_media": featured_media
    }
    response = requests.post(api_url,headers=wordpress_header, json=data)
    new_post_id = response.json()["id"]
    post_url = response.json()["link"]
    return new_post_id, post_url
    print(response)


### picture download and upload

def download_image(image_url, folder_path, file_name):
    response = requests.get(image_url)
    if response.status_code == 200:
        image_data = BytesIO(response.content)
        img = Image.open(image_data)
        
        # Convert the image to JPG format
        img = img.convert('RGB')        
        file_name = file_name
        jpg_file_path = os.path.join(folder_path, os.path.splitext(file_name)[0] + '.jpg')
        img.save(jpg_file_path, format='JPEG')
        
        return jpg_file_path
    else:
        print("Image download failed.")
        return None

def upload_media(image_path, authname, authpass):
    api_url = '###/wp-json/wp/v2/media'
    with open(image_path, 'rb') as image_file:
        data = image_file.read()
    headers = {
        'Content-Type': 'image/jpg',
        'Content-Disposition': f'attachment; filename={os.path.basename(image_path)}'
    }
    metadata = {
        'alt_text': "alt_text",
        'title': "title_text"
    }
    res = requests.post(
        url=api_url,
        data=data,
        headers=headers,
        auth=(authname, authpass)
    )
    if res.status_code == 201:  # HTTP 201 Created indicates success
        newDict = res.json()
        newID = newDict.get('id')
        link = newDict.get('guid').get("rendered")
        #print(newID, link)
        picture_id = newID
        return picture_id, link
    else:
        print("Media upload failed.")
        return None, None

# GetYourGuide Stuff
## FUNCTIONS
def gyg_city_widget(country, results):
    tracking_code = country + "_sights"
    widget_url = f'<div data-gyg-href="https://widget.getyourguide.com/default/activities.frame" data-gyg-locale-code="de-DE" data-gyg-widget="activities" data-gyg-number-of-items="{results}" data-gyg-cmp="{tracking_code}" data-gyg-partner-id="###" data-gyg-q="{country}"></div>'
    return widget_url, tracking_code

### open street map function
def get_coordinates(location_name):
    base_url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": location_name,
        "format": "json"
    }
    response = requests.get(base_url, params=params)
    return response.json()


for country in country_list:
    n = random.randint(n_start,n_end)
    print(f"{country}: {n} Sights.")

    
    #prompts
    act_as_prompt = f"Ich möchte, dass du als SEO-Redakteur für ein Online-Magazin agierst, dass ich mit dem Thema Sehenswürdigkeiten der gesamten Welt beschäftigt. Du integrierst Keywords so in die Artikel, dass die Inhalte gut in den Suchergebnissen platziert werden. Du verfasst informative Artikel. Du recherchierst gründlich, um fundierte Informationen zu liefern. Du achtest auf eine gute Struktur. Du integrierst sinnvolle Keywords ohne den Lesefluss zu stören. Du schreibst aus der Ich-Perspektive, bist mit den Lesern Per Du. Du gibst Ratschläge auf Basis deiner Erfahrung in {country}, schreibst aber nicht, dass du SEO-Redakteur bist. Du schreibst Kurz und Knackig."
    structure_prompt = f"Welche Top {n} Sehenswürdigkeiten muss man in {country} unbedingt gesehen haben? Schreibe mir kein einziges Wort, außer die Sehenswürdigkeiten als Python Liste formatiert. Vermeide Sehenswürdigkeiten, die einen geschützten Marken-Namen tragen. Formuliere den Namen der Sehenswürdigkeit so, dass ich über OpenStreetMap API die Geolocation korrekt abfragen kann."
    header_pic_prompt = f"Bild von {country}, aufgenommen mit einem Weitwinkelobjektiv."
    introduction_prompt = f"Schreibe eine Einleitung für einen Artikel, bei dem es um Sehenswürdigkeiten in {country} geht. Länge: Maximal 50 Wörter. Beschreibe, was {country} für Touristen ausmacht und warum man unbedingt {country} besuchen soll. Du bist Per Du mit der Leserschaft."
    in_one_tag_prompt = f"Maximal 70 Wörter: Ich habe einen Tag Zeit für die wichtigsten Sehenswürdigkeiten in {country}. Welche soll ich mir ansehen? Welche gehen sich realistisch aus, wenn ich mit einen Mietauto unterwegs bin? Beschränke die Auswahl auf einen Ort. Kein Titel notwendig. Du bist Per Du mit der Leserschaft."
    in_two_tag_prompt = f"Maximal 70 Wörter: Ich habe zwei Tage Zeit für die wichtigsten Sehenswürdigkeiten in {country}. Welche soll ich mir ansehen? Welche gehen sich realistisch aus, wenn ich mit einen Mietauto unterwegs bin? Beschränke die Auswahl auf einen Ort. Kein Titel. Du bist Per Du mit der Leserschaft."
    in_three_tag_prompt = f"Maximal 70 Wörter: Ich habe drei Tage Zeit für die wichtigsten Sehenswürdigkeiten in {country}. Welche soll ich mir ansehen? Welche gehen sich realistisch aus, wenn ich mit einen Mietauto unterwegs bin? Beschränke die Auswahl auf zwei Orte, die nahe beinander liegen. Kein Titel. Du bist Per Du mit der Leserschaft."
    in_four_tag_prompt = f"Maximal 70 Wörter: Ich habe vier Tage Zeit für die wichtigsten Sehenswürdigkeiten in {country}. Welche soll ich mir ansehen? Welche gehen sich realistisch aus, wenn ich mit einen Mietauto unterwegs bin? Beschränke die Auswahl auf drei Orte, die nahe beinander liegen. Kein Titel. Du bist Per Du mit der Leserschaft."
    #print("Prompts set.")
    
    #self_written content
    title_tag = f"Top {n} Sehenswürdigkeiten in {country}: Karte, Tickets & mehr"
    #print(f"{country}: Title Tag ✅.")

    
    different_day_sights_content = "<h2>Welche Sehenswürdigkeiten sollte man in 1, 2, 3 oder 4 Tagen gesehen haben?</h2>"
    more_regions_to_explore_h2_header = f"<br><h2>Du möchtest mehr aus {country_name} entdecken? Finde Sehenswürdigkeiten aus der Region:</h2>"
    more_regions_to_explore_linklist = f"[catlist id={category_id}]"
    #Call Functions for...

    # Header Pic
    header_pic, header_pic_cost = openAI_picture(header_pic_size, header_pic_prompt)
    #print(f"{country}: Header Pic ✅. ({header_pic_cost}USD).")
    
    #Intro & Outro content
    intro_content, intro_content_cost = openAI_content(act_as_prompt, introduction_prompt)
    #print(f"{country}: Intro Content ✅. ({intro_content_cost}USD).")
    outro_content = f"{country} ist großartig - doch nicht immer sind für alle Geschmäcker interessante Sehenswürdigkeiten dabei. Wenn dich also der Charme noch nicht erobert hat hast du nachfolgend die Möglichkeit noch etliche weitere Angebote für spannende Touren, einzigartige Rundgänge, geführte Entdeckungen und mehr zu buchen."
    #print(f"{country}: Outro Content ✅.")

    #map content generation+
    map_content = f"{country} hat viele Sehenswürdigkeiten, Attraktionen und Geheimtipps zu bieten. Damit du dich leichter zurechtfindest, habe ich dir auf der Karte die wichtigsten Sehenswürdigkeiten von {country} markiert."
    #print(f"{country}: Map Content ✅.")
    

    

    
    ### Things to See over different days
    one_day_sights, one_day_sights_cost = openAI_content(act_as_prompt, in_one_tag_prompt)
    if one_day_sights.startswith('"') and one_day_sights.endswith('"'):
        one_day_sights = one_day_sights[1:-1]
    else:
        one_day_sights = one_day_sights
    #print(f"{country}: One Day Sights ✅. ({one_day_sights_cost}USD).")

    two_day_sights, two_day_sights_cost = openAI_content(act_as_prompt, in_two_tag_prompt)
    if two_day_sights.startswith('"') and two_day_sights.endswith('"'):
        two_day_sights = two_day_sights[1:-1]
    else:
        two_day_sights = two_day_sights
    #print(f"{country}: Two Day Sights ✅. ({two_day_sights_cost}USD).")

    three_day_sights, three_day_sights_cost = openAI_content(act_as_prompt, in_three_tag_prompt)
    if three_day_sights.startswith('"') and three_day_sights.endswith('"'):
        three_day_sights = three_day_sights[1:-1]
    else:
        three_day_sights = three_day_sights
    #print(f"{country}: Three Day Sights ✅. ({three_day_sights_cost}USD).")

    four_day_sights, four_day_sights_cost = openAI_content(act_as_prompt, in_four_tag_prompt)
    if four_day_sights.startswith('"') and four_day_sights.endswith('"'):
        four_day_sights = four_day_sights[1:-1]
    else:
        four_day_sights = four_day_sights
    #print(f"{country}: Four Day Sights ✅. ({four_day_sights_cost}USD).")

    #Article Structure
    top_sights, top_sights_cost = openAI_content(act_as_prompt, structure_prompt)
    # check if gpt actually returned a list or not
    try:
        input_list = json.loads(top_sights)
        if isinstance(input_list, list) and all(isinstance(item, str) for item in input_list):
            # The input is already a valid list of strings
            output_list = input_list
        else:
            # The input is not a valid list, try parsing as a string list
            input_list = [item.strip("' ") for item in top_sights.strip("[]").split(",")]
            output_list = json.dumps(input_list, ensure_ascii=False)
    except json.JSONDecodeError:
        # The input is not a valid JSON, parse as a string list
        input_list = [item.strip("' ") for item in top_sights.strip("[]").split(",")]
        output_list = json.dumps(input_list, ensure_ascii=False)
    sight_list = output_list
    #print(f"{country}: Top Sights ✅. ({top_sights_cost}USD).")
    
    ##### HTML BUILDING #####################
    slug = country
    toc = '<!-- wp:simpletoc/toc {"max_level":2} /-->' + '<hr class="wp-block-separator has-css-opacity"/>'
    explore_more_text = f"<!-- wp:heading --> <h2 class='wp-block-heading'>Entdecke mehr Aktivitäten in {country}</h2> <!-- /wp:heading -->"
    explore_more_for_this_sight_content = f"<!-- wp:paragraph --> <p>{outro_content}</p>"
    explore_more_widget, tracking_code = gyg_city_widget(country, 12)
    header_pic_url = header_pic
    header_picture_path = download_image(header_pic_url, folder_path, country)
    header_picture_id, header_picture_link = upload_media(header_picture_path, wordpress_user, wordpress_password)
 
    amazon_reisefuhrer_link = f'<a href="https://www.amazon.de/gp/search?ie=UTF8&tag=###&linkCode=ur2&linkId=8d3acd281990faaeeee95aee69ed62ec&camp=1638&creative=6742&index=aps&keywords=Reiseführer {country}" target="_blank" >Amazon(*)</a>'
    intro_content = intro_content + "<br><br>" f"<p><b>Hinweis:</b> Du hast deine Reise nach {country} noch nicht gebucht? Dann empfehle ich dir einen kompakten Reiseführer für {country} für dein Handgepäck zu kaufen (z.B. auf {amazon_reisefuhrer_link})  - damit deine Erkundungstour vor Ort ein unvergessliches Erlebnis wird.</p><br>" + "<hr class='wp-block-separator has-css-opacity'/>"
    
    map_content_h2 = "<!-- wp:heading --> <h2 class='wp-block-heading'>" + f"Karte aller Sehenswürdigkeiten in {country}" + "</h2> <!-- /wp:heading -->"
    tour_one_day_h3 = f"<!-- wp:heading --> <h3 class='wp-block-heading'>{country} Sehenswürdigkeiten in 1 Tag:</h3> <!-- /wp:heading -->"
    tour_two_day_h3 = f"<!-- wp:heading --> <h3 class='wp-block-heading'>{country} Sehenswürdigkeiten in 2 Tagen:</h3> <!-- /wp:heading -->"
    tour_three_day_h3 = f"<!-- wp:heading --> <h3 class='wp-block-heading'>{country} Sehenswürdigkeiten in 3 Tagen:</h3> <!-- /wp:heading -->"
    tour_four_day_h3 = f"<!-- wp:heading --> <h3 class='wp-block-heading'>{country} Sehenswürdigkeiten in 4 Tagen:</h3> <!-- /wp:heading -->"
    
    one_and_two_days_sights_content = '<!-- wp:columns --> <div class="wp-block-columns"><!-- wp:column --> <div class="wp-block-column">' + tour_one_day_h3 + '<!-- wp:paragraph --> <p>' + one_day_sights + '</p> <!-- /wp:paragraph --></div> <!-- /wp:column --> <!-- wp:column --> <div class="wp-block-column">' + tour_two_day_h3 + '<!-- wp:paragraph --><p>' + two_day_sights + '</p> <!-- /wp:paragraph --></div> <!-- /wp:column --></div> <!-- /wp:columns --><br>'
    three_and_four_days_sights_content = '<!-- wp:columns --> <div class="wp-block-columns"><!-- wp:column --> <div class="wp-block-column">' + tour_three_day_h3 + '<!-- wp:paragraph --><p>' + three_day_sights + '</p> <!-- /wp:paragraph --></div> <!-- /wp:column --> <!-- wp:column --> <div class="wp-block-column">' + tour_four_day_h3 + '<!-- wp:paragraph --><p>' + four_day_sights + '</p> <!-- /wp:paragraph --></div> <!-- /wp:column --></div> <!-- /wp:columns --><br>'
    
    #########################################
    # Lists for Sight Costs
    sight_content_costs = []
    sight_picture_costs = []
    content_all_html = []
    sight_data_for_schema = []  # List to store sight coordinates
    sight_coordinates = []  # List to store sight coordinates

    i = 0

    #variables for wikipedia
    ### Schema Implementation
    wiki_wiki = wikipediaapi.Wikipedia('(###) - baue mit den Infos ein Schema.org Script, siehe https://schema.org/TouristDestination', 'de')

    schema_name = country + " Sehenswürdigkeiten"
    schema_description = f"Die schönsten Sehenswürdigkeiten von {country} im Überblick."
    schema_url = slug
    #H2: Headlines, Content and Pictures
    for sight in sight_list:
        i += 1
        
        ### PROMPTS ###
        content_prompt = f"Maximal 100 Wörter. Erzähle etwas über {sight}. Was macht sie so besonders? Warum muss man als Tourist dort hin? Was zeichnet diese Sehenswürdigkeit aus im Vergleich zu anderen Sehenswürdigkeiten in {country}? Du bist Per Du mit der Leserschaft."
        content_pic_prompt = f"Bild von der Sehenswürdigkeit {sight}, aufgenommen mit einem Weitwinkelobjektiv direkt vor der Sehenswürdigkeit."
        
        ###############
        
        request_sight_content, sight_content_cost = openAI_content(act_as_prompt, content_prompt)
        sight_content = '<!-- wp:column {"width":"66.66%"} --> <div class="wp-block-column" style="flex-basis:66.66%"><!-- wp:paragraph --> <p>'+ request_sight_content + '</p> <!-- /wp:paragraph --></div> <!-- /wp:column --></div> <!-- /wp:columns --><br>'
        sight_content_costs.append(sight_content_cost)
        #print(f"{country}: Sight Content ✅. ({sight_content_cost}USD).")
        
        sight_h2 = "<!-- wp:heading --> <h2 class='wp-block-heading'>" + f"{i}. {sight}" + "</h2> <!-- /wp:heading -->"
        #print(f"{country}: H2 ✅.")
        
        alt_tag = f"{sight} erstrahlt in vollem Glanz: Aufgenommen mit einem Weitwinkelobjektiv direkt vor dieser atemberaubenden Sehenswürdigkeit in {country}"
        #print(f"{country}: Alt Tag ✅.")

        request_sight_picture, sight_picture_cost = openAI_picture(content_pic_size, content_pic_prompt)
        sight_encoded = base64.b64encode(sight.encode()).decode()
        if request_sight_picture is not None:
            image_path = download_image(request_sight_picture, folder_path, sight_encoded)
            picture_id, link = upload_media(image_path, wordpress_user, wordpress_password)
            sight_picture_url = link
            picture_id = str(picture_id)
            sight_pic = '<!-- wp:columns --> <div class="wp-block-columns"><!-- wp:column {"width":"33.33%"} --> <div class="wp-block-column" style="flex-basis:33.33%"><!-- wp:image {"align":"center","id":316,"sizeSlug":"full","linkDestination":"none","className":"is-style-default"} --> <figure class="wp-block-image size-full is-style-default"><img src="' + f'{link}"' + f' alt="{alt_tag}" class="wp-image-' + picture_id + '"/></figure><!-- /wp:image --></div> <!-- /wp:column -->'
            sight_picture_costs.append(sight_picture_cost)
        else:
            print(f"No Content Pic for {sight} due to saftey system restrictions")
        #print(f"{country}: Content Pic ✅. ({sight_picture_cost}USD).")

        explore_more_for_this_sight_heading = f"<!-- wp:heading --> <h3 class='wp-block-heading'>Tour & Tickets für {sight}: Jetzt buchen!</h3> <!-- /wp:heading -->"
        explore_more_for_this_sight, tracking_code = gyg_city_widget(sight, 3)
        seperator = "<hr class='wp-block-separator has-css-opacity'/><br>"

        ### schema pic link
        location_name = sight
        result = get_coordinates(location_name)

        if result and isinstance(result, list):
            first_result = result[0]  # Take the first result
            sight_latitude = float(first_result.get("lat"))
            sight_longitude = float(first_result.get("lon"))
            location_name = first_result["name"]
            try:
                page = wiki_wiki.page(location_name)
                wiki_url = page.fullurl
                #print("Wiki URL: ", wiki_url)
            except Exception as e:
                wiki_url = ""
                #print("No Wiki URL for ", location_name)
                pass
            sight_data_for_schema.append((location_name, sight_latitude, sight_longitude, wiki_url, sight_picture_url))  # Add coordinates to the list
            #print("Sight Data for Schema appended")
        else:
            print("No Wiki Result found in List for ", location_name)
        
        #build map content
        location_name = sight
        result = get_coordinates(location_name)

        if result and isinstance(result, list):
            first_result = result[0]  # Take the first result
            sight_latitude = float(first_result.get("lat"))
            sight_longitude = float(first_result.get("lon"))
            sight_coordinates.append((sight_latitude, sight_longitude))  # Add coordinates to the list
            #print("Map Content Coordinations appended for ", location_name)
        else:
            print("No Coordinations found for ", location_name)
            
        #### BUILD HTML ###
        content_all_html.append(sight_h2)
        content_all_html.append(sight_pic)
        content_all_html.append(sight_content)
        content_all_html.append(explore_more_for_this_sight_heading)
        content_all_html.append(explore_more_for_this_sight)
        content_all_html.append(seperator)
        print(f"Sehenswürdigkeit {i}/{n} fertig.")
    

    # Get the coordinates of the country or city
    location_data = get_coordinates(country)
    if location_data and isinstance(location_data, list):
        first_result = location_data[0]  # Take the first result
        location_lat = float(first_result.get("lat"))
        location_lon = float(first_result.get("lon"))
    else:
        print(f"Location not found for {country}.")
    
    #build map
    m = folium.Map(location=[location_lat, location_lon], zoom_start=zoom_level)

    for sight_coord, sight_name in zip(sight_coordinates, sight_list):
        folium.Marker(
            location=sight_coord,
            popup=sight_name,
        ).add_to(m)
    
    # Save the map to an HTML file & upload
    map_path = folder_path + f"/map_{country}.html"
    m.save(map_path)
    
    #### add meta tags to map html
    # Read the original HTML file
    with open(map_path, 'r') as file:
        html_content = file.read()

    # Add desired meta tags
    meta_description = f"Top {n} Sehenswürdigkeiten in {country}: 1. {sight_list[0]}, 2. {sight_list[1]}, 3. {sight_list[2]} und mehr ❤️ Jetzt Tickets buchen"
    #print(f"{country}: Meta Description ✅.")    
    
    meta_tags_map = """
    <meta name="robots" content="noindex">
    <meta name="googlebot" content="indexifembedded">
    """

    # Insert the meta tags into the <head> section of the HTML content
    insert_position = html_content.find('</head>')
    if insert_position != -1:
        modified_html_content = html_content[:insert_position] + meta_tags_map + html_content[insert_position:]
    else:
        modified_html_content = html_content  # Fallback if <head> section not found
    # Save the modified HTML content back to the file
    with open(map_path, 'w') as file:
        file.write(modified_html_content)
    #print("Meta tags added to Sights Map")
    
    #upload map to wordpress
    map_id, map_url = upload_media(map_path, wordpress_user, wordpress_password)
    map_iframe = f'<iframe src="{map_url}" width="100%" height="400" frameborder="0"></iframe><br>'


    #sum up costs of sights
    total_sight_content_cost = sum(sight_content_costs)
    total_sight_picture_cost = sum(sight_picture_costs)   

    # META TAGS
    meta_tags = f"<meta name='description' content='{meta_description}'>"
    ### building schema
    
    initial_attractions = []
    for attraction_name, latitude, longitude, wikipedia_url, sight_picture_url in sight_data_for_schema:
        attraction = {"@type": ["TouristAttraction"],"name": attraction_name,"geo": {"@type": "GeoCoordinates","latitude": str(latitude),"longitude": str(longitude)},"sameAs": wikipedia_url,"image": sight_picture_url}
        initial_attractions.append(attraction)

    schema_data = {"@context": "https://schema.org","@type": "TouristDestination","name": schema_name,"description": schema_description,"includesAttraction": initial_attractions}
    schema_json = json.dumps(schema_data, indent=2)
    # Wrap the schema_json with <script> tags
    script_start = '<script type="application/ld+json">'
    script_end = '</script>'
    schema_with_script = script_start + schema_json + script_end

    ################################################################################################
    # WORDPRESS PUBLISHING #
    ################################################################################################
    # delimiting
    above_the_fold_content = intro_content + schema_with_script + toc + map_content_h2 + map_content + map_iframe
    delimiter = "´"  # You can change this to whatever separator you want
    content_all_html = delimiter.join(content_all_html)
    content_all_html = meta_tags + above_the_fold_content + content_all_html + different_day_sights_content + one_and_two_days_sights_content + three_and_four_days_sights_content + seperator + explore_more_text + explore_more_for_this_sight_content + explore_more_widget + more_regions_to_explore_h2_header + more_regions_to_explore_linklist
    content_all_html = content_all_html.replace(delimiter, '')
    
    # PUBLISH TO WORDPRESS
    new_post_id, wp_post_url = create_wordpress_post(
        title=title_tag,
        slug=slug,
        content=content_all_html,
        excerpt=meta_description, 
        category = category_id,
        featured_media = header_picture_id
    )
    ################################################################################################
    #TOTAL COST CALCULATION
    total_cost = (
        header_pic_cost +
        intro_content_cost +
        top_sights_cost +
        total_sight_content_cost +
        total_sight_picture_cost +
        one_day_sights_cost + 
        two_day_sights_cost +
        three_day_sights_cost + 
        four_day_sights_cost
    )
    rounded_total_cost = round(total_cost, 3)
    print(f"#################### Der Artikel für {country} hat {rounded_total_cost}USD gekostet. URL: {wp_post_url}")
