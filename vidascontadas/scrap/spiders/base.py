# coding=utf-8
from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor

import scrap.items as items
from common.models import CustomDate
from cities_light.models import City
from places.models import Place

from bs4 import BeautifulSoup

import re
import csv

def get_int_from_text(expression, sub, text):
    re_result = re.search(expression, text, re.M|re.I|re.U)
    return int(re.sub(sub, '', re_result.group())) if re_result else 0

def extract_text(expression, text):
    re_result = re.search(expression, text, re.M|re.I|re.U)
    return re_result.groups()[0] if re_result else ""

def get_place_from_text(place_html):
    city_query = City.objects

    #region
    region_html = place_html.findNext(text=re.compile('Provincia: \w+'))
    region_text = re.sub('Provincia: ', '', region_html)
    if not region_text == u'No informa/Ez du informatzen':
        city_query = city_query.filter(region__name__iexact=region_text)
        if not city_query:
            pass
            #TODO
            #send mail with data to add to db

    #city
    city_html = place_html.find_next(text=re.compile('Municipio: \w+'))
    city_text = re.sub('Municipio: ', '', city_html)
    if not city_text == u'No informa/Ez du informatzen':
        city_query = city_query.filter(name__iexact=city_text)
        if not city_query:
            pass
            #TODO
            #send mail with data to add to db

    city = None
    if city_query != City.objects and city_query:
        if len(city_query) > 1:
            pass
            #TODO
            #send mail to detect duplication cities
        else:
            city = city_query[0]

    name = ''
    #neighbourhood
    neighbourhood_html = place_html.find_next(
                         text=re.compile('Concejo o barrio: \w+'))
    neighbourhood_text = re.sub('Concejo o barrio: ', '', neighbourhood_html)
    if not neighbourhood_text == u'No informa/Ez du informatzen':
        name += neighbourhood_text

    #subregion
    subregion_html = place_html.find_next(
                         text=re.compile('Comarca: \w+'))
    subregion_text = re.sub('Comarca: ', '', subregion_html)
    if not subregion_text == u'No informa/Ez du informatzen':
        name += subregion_text

    #get place
    places = Place.objects

    places = places.filter(city=city) if city else places.none()

    if name != '' or places:
        place, created = places.get_or_create(name=name)
        place.save()
        return place
    else:
        return None

class DemoSpider(CrawlSpider):
    name = 'base'
    allowed_domains = ['memoria-oroimena.unavarra.es', ]

    start_urls = [
            'http://memoria-oroimena.unavarra.es/es/buscar/?pax=1', ]

    ofile  = open('ttest.csv', "wb")
    writer = csv.writer(ofile, delimiter='\t', quotechar='"', quoting=csv.QUOTE_ALL)  

    cabecera = ["Nombre","Sexo","Edad",
        "Profesión","Cargo","Filiación","Partido/Sindicato",
        "Fecha nacimiento - Año","Fecha nacimiento - Mes","Fecha nacimiento - Día",
        "Fecha muerte - Año","Fecha muerte - Mes","Fecha muerte - Día",
        "Nacimiento - Concejo o barrio", "Nacimiento - Municipio", "Nacimiento - Comarca", "Nacimiento - Provincia",
        "Vecindad - Concejo o barrio", "Vecindad - Municipio", "Vecindad - Comarca", "Vecindad - Provincia",
        "Muerte - Concejo o barrio", "Muerte - Municipio", "Muerte - Comarca", "Muerte - Provincia",
        ]

    writer.writerow(cabecera)

    def location_href_value(value):
        m = re.search("location.href=\'(.*)\'", value)
        return m.groups()[0]

    rules = [
        Rule(SgmlLinkExtractor(
            allow=['/es/buscar/\?pax=\d+'], unique=True), follow=True),
        Rule(SgmlLinkExtractor(
            allow=['.*'], tags=('div'), attrs=('onclick'), unique=True,
            process_value=location_href_value), 'parse_item'),]
      
    def parse_item(self, response):

        data=re.sub('<br>',' ',response.body)

        html = BeautifulSoup(data)

        ficha = html.find('div', {'class':'ficha_desc'})

        #fields

        name = ficha.find('h2').text
        genre_html = ficha.find('p', 't1').next_element
        birth_year=get_int_from_text(u'A\xf1o: \d{4}','A\xf1o: ',ficha.text)
        birth_month=get_int_from_text(u'Mes: \d{4}','Mes: ',ficha.text)
        birth_day=get_int_from_text(u'D\xeda: \d{4}','D\xeda: ',ficha.text)
        age = get_int_from_text(u'Edad: \d{1,3}','Edad: ',ficha.text)

        lugares = re.findall(ur'Concejo o barrio: (.*?) Municipio: (.*?) Comarca: (.*?) Provincia: ([a-zA-Z\/]*)',ficha.text, re.M|re.I|re.U)

        concejo_o_barrio_nac = lugares[0][0]
        municipio_nac = lugares[0][1]
        comarca_nac = lugares[0][2]
        provincia_nac = lugares[0][3]

        concejo_o_barrio_vec = lugares[1][0]
        municipio_vec = lugares[1][1]
        comarca_vec = lugares[1][2]
        provincia_vec = lugares[1][3]


        politica = re.findall(u'Profesión: (.*?) Ocupó el cargo de: (.*?) Filiación sociopolítica: (.*?) Partido/Sindicato: (.*?) ',ficha.text, re.M|re.I|re.U)
        profesion = politica[0][0]
        cargo = politica[0][1]
        filiacion = politica[0][2]
        partido = politica[0][3]

        ficha2 = html.find('div', {'class':'ficha_desc_derecha'})

        death_year=get_int_from_text(u'A\xf1o: \d{4}','A\xf1o: ',ficha2.text)
        death_month=get_int_from_text(u'Mes: \d{4}','Mes: ',ficha2.text)
        death_day=get_int_from_text(u'D\xeda: \d{4}','D\xeda: ',ficha2.text)

        concejo_o_barrio_muerte = extract_text(u'Concejo o barrio: (\w+)',ficha2.text)
        municipio_muerte = extract_text(u'Municipio: (\w+)',ficha2.text)
        comarca_muerte = extract_text(u'Comarca: (\w+)',ficha2.text)
        provincia_muerte = extract_text(u'Provincia: ([a-zA-Z\/]*)',ficha2.text)


        item = items.PeopleItem()
        item['url'] = response.url

        #name
        item['name'] = name

        #genre
        item['genre'] = 'F' if genre_html == 'Mujer'\
                        else 'M' if genre_html == 'Hombre'\
                        else 'U'

        #birth date
        date_birth, created = CustomDate.objects.get_or_create(
                 year=get_int_from_text(u'A\xf1o: \d{4}','A\xf1o: ',ficha.text),
                 month=get_int_from_text(u'Mes: \d{4}','Mes: ',ficha.text),
                 day=get_int_from_text(u'D\xeda: \d{4}','D\xeda: ',ficha.text))
        date_birth.save()
        item['date_birth'] = date_birth

        #Age
        item['age'] = age

        #birth places
        birth_place_html = ficha.find(text='Lugar de nacimiento')
        item['place_birth'] = get_place_from_text(birth_place_html)

        item.save()

        row = []
        row.append(name.encode("utf-8"))
        row.append(genre_html)        
        row.append(age)
        row.append(profesion.encode("utf-8"))
        row.append(cargo.encode("utf-8"))
        row.append(filiacion.encode("utf-8"))
        row.append(partido.encode("utf-8"))
        row.append(birth_year)
        row.append(birth_month)
        row.append(birth_day)
        row.append(death_year)
        row.append(death_month)
        row.append(death_day)        
        row.append(concejo_o_barrio_nac.encode("utf-8"))
        row.append(municipio_nac.encode("utf-8"))
        row.append(comarca_nac.encode("utf-8"))
        row.append(provincia_nac.encode("utf-8"))
        row.append(concejo_o_barrio_vec.encode("utf-8"))
        row.append(municipio_vec.encode("utf-8"))
        row.append(comarca_vec.encode("utf-8"))
        row.append(provincia_vec.encode("utf-8"))
        row.append(concejo_o_barrio_muerte.encode("utf-8"))
        row.append(municipio_muerte.encode("utf-8"))
        row.append(comarca_muerte.encode("utf-8"))
        row.append(provincia_muerte.encode("utf-8"))

        print name
        self.writer.writerow(row)

        return item

