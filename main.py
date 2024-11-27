import os, sys, json, requests, time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from dotenv import load_dotenv
load_dotenv()


hello = """
>>>[ACADEMICA SIIA EXTRACTOR]
Integración con SIIA - UAM.

WebScraper para la extracción de datos del
Sistema Integral de Inforemación Académica
de la UAM Xochimilco.

Autor: Daniel Limón
Email: dani@dlimon.net

"""

print(hello)

# Headless Mode
options = webdriver.ChromeOptions()
# options.add_argument("--headless")
# options.add_argument("--no-sandbox")
# options.add_argument("--disable-dev-shm-usage")

print("> [Iniciando navegador]")
driver = webdriver.Chrome(options=options)

# Obtener las dimensiones de la pantalla principal
screen_width = driver.execute_script("return window.screen.availWidth")
screen_height = driver.execute_script("return window.screen.availHeight")

print("> [Navegador iniciado]\n")

#driver.set_window_size(width = 500, height = 850)
driver.set_window_size(screen_width // 2, screen_height)

print("> [Entrando a SIIA]\n")
url = os.getenv('SIIA_XOC_URI')
driver.get(url)
print("> [Login de SIIA cargado]\n")

# Encontrar campos de login
username_input = driver.find_element(By.ID, "ufld:CD_USUARIO.CONTROLES.ED01:AELCWBAWS003.1")
password_input = driver.find_element(By.ID, "ufld:CD_CONTRASENA.CONTROLES.ED01:AELCWBAWS003.1")

username_input.send_keys(os.getenv('SIIA_USERNAME'))
password_input.send_keys(os.getenv('SIIA_PASSWORD'))
#input("Hey")
driver.find_element(By.ID, "ufld:CD_INGRESAR.CONTROLES.ED01:AELCWBAWS003.1").click()
# Comentario
print("> [Enviando credenciales]\n")

try:
    WebDriverWait(driver, 20).until(
        EC.presence_of_all_elements_located((By.ID, "ufld:CD_SALIR.CONTROL.ED01:AELCWBAWT002.1")))
    print("> [Acceso a SIIA exitoso!]\n")
except Exception as e:
    print('Error al acceder a SIIA')
    driver.quit()

print("> [Accediendo a CURSOS POR COORDINACIÓN]\n")

driver.find_element(By.ID, "ufld:OPCION_WEB_DOC_DE.OPCION_WEB_DOCENCIA.RH02:AELCWBAWT002.5").click()

try:
    WebDriverWait(driver, 20).until(
        EC.presence_of_all_elements_located((By.ID, "uent:E_UEA.PE02:AELCWBAWT011")))
    print("> [Cursos obtenidos]\n")
except Exception as e:
    print('Error cargando "Cursos por coordinación"')
    driver.quit()

cursos_table = driver.find_element(By.ID, "uent:E_UEA.PE02:AELCWBAWT011")
cursos_rows = cursos_table.find_elements(By.XPATH, ".//tr[@id]")
cursos_data = []

for row in cursos_rows:
    # Encuentra el elemento <a> dentro de la fila
    link = row.find_element(By.XPATH, ".//a")
    # Encuentra el nombre en la misma fila
    name = row.find_element(By.XPATH, ".//span[contains(@id, 'NOM_OF_UEA_NO')]")
    
    # Guarda el link y el nombre en la lista
    cursos_data.append({
        "link": link,
        "name_text": name.text
    })

    # html_content = row.get_attribute('outerHTML')
    # print(html_content)  # Imprime el HTML de cada fila


for curso in cursos_data:
    print(f"> [{cursos_data.index(curso)}] - {curso['name_text']}")

uea_selected = int(input("\nSeleccione UEA a extraer > "))
if isinstance(uea_selected, int) and uea_selected < len(cursos_data):


    # Mercado y competencia entre capitales
    print(f"> [Accediendo a grupos para {cursos_data[uea_selected]['name_text']}]\n")
    cursos_data[uea_selected]['link'].click()
    try:
        WebDriverWait(driver, 60).until(
            EC.presence_of_all_elements_located((By.ID, "uent:CURSOS.AE02:AELCWBAWT012")))
        print("> [Grupos obtenidos]\n")
    except Exception as e:
        print('Error cargando Módulos')
        driver.quit()

    grupos_table = driver.find_element(By.ID, "uent:CURSOS.AE02:AELCWBAWT012")

    grupos_data = []
    grupos_rows = grupos_table.find_elements(By.XPATH, ".//tbody/tr")

for row in grupos_rows:
    try:
        # Eliminación de tablas anidadas no deseadas
        nested_tables = row.find_elements(By.XPATH, './/td/table')
        for nested_table in nested_tables:
            driver.execute_script("arguments[0].remove();", nested_table)

        grupo = row.find_element(By.XPATH, './/td[2]').text.strip()
        boton = row.find_element(By.XPATH, './/td[10]/a')

        # Agregar el `id` del botón en lugar del `xpath`
        grupos_data.append({
            'grupo': grupo,
            'boton_id': boton.get_attribute("id")
        })
    except Exception as e:
        print(f"Error al procesar la fila: {e}")


    ###
# print(grupos_data)
# input(".")
# Iterar sobre `grupos_data` para hacer clic y extraer datos
for i in grupos_data:
    print(f"> [Accediendo a grupo {i['grupo']}]\n")
    
    # Localiza el botón por `id` antes de hacer clic
    boton = driver.find_element(By.ID, i['boton_id'])
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, i['boton_id'])))
    boton.click()

    try:
        time.sleep(2)
        WebDriverWait(driver, 60).until(
            EC.presence_of_all_elements_located((By.ID, "uent:ALUMNO_V_ACAD.AE02:AELCWBAWT013.1"))
        )
        table = driver.find_element(By.ID, 'uent:ALUMNO_V_ACAD.AE02:AELCWBAWT013.1')
        print("> [Información de grupo cargada]\n")
    except Exception as e:
        print('Error cargando lista de grupo')
        driver.quit()

    print("> [Serializando información]\n")
    
    grupo_lista_data = []
    rows = table.find_elements(By.XPATH, ".//tbody/tr")

    for row in rows:
        numero = row.find_element(By.XPATH, "./td[1]/span").text
        matricula = row.find_element(By.XPATH, "./td[2]/span").text
        nombre = row.find_element(By.XPATH, "./td[3]/span").text
        #correo = row.find_element(By.XPATH, ".td[4]/span").text
        
        grupo_lista_data.append({
            'Numero': numero,
            'Matricula': matricula,
            'Nombre': nombre,
            #'Correo': correo
        })

    with open(f'{i["grupo"]}_{cursos_data[uea_selected]["name_text"]}_grupo.json', 'w', encoding='utf-8') as json_file:
        json.dump(grupo_lista_data, json_file, ensure_ascii=False, indent=4)
    print("> [Datos guardados en formato JSON]\n")

    print("> [INFORMACIÓN EXTRAÍDA DEL SISTEMA]\n")
    print(json.dumps(grupo_lista_data, indent=2))
    grupo_lista_data = []

    # Clic para regresar
    regresar_boton = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "ufld:CD_REGRESAR.CONTROLES.ED01:AELCWBAWT012.1"))
    )
    regresar_boton.click()

    try:
        time.sleep(2)
        WebDriverWait(driver, 60).until(
            EC.presence_of_all_elements_located((By.ID, "uent:CURSOS.AE02:AELCWBAWT012"))
        )
        print("> [Grupos obtenidos]\n")
    except Exception as e:
        print('Error cargando Módulos')
        driver.quit()
        


