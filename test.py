from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import json, requests

# Headless Mode
options = webdriver.ChromeOptions()
# options.add_argument("--headless")
# options.add_argument("--no-sandbox")
# options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(options=options)

url = "file:///home/d/Downloads/siia.html"
driver.get(url)

# Localiza la tabla
table = driver.find_element(By.ID, "uent:CURSOS.AE02:AELCWBAWT012")

# Extrae encabezados
headers = [header.text for header in table.find_elements(By.XPATH, ".//thead/tr/th")]
desired_headers = ["TRIMESTRE", "GRUPO", "ACTA", "INSCRITOS", "LISTA DE GRUPO"]

# Extrae datos de las filas
data = []
rows = table.find_elements(By.XPATH, ".//tbody/tr")

for i in range(len(rows)):
    try:
        # Vuelve a localizar la tabla y las filas en cada iteración
        table = driver.find_element(By.ID, "uent:CURSOS.AE02:AELCWBAWT012")
        rows = table.find_elements(By.XPATH, ".//tbody/tr")
        
        # Verifica si el índice `i` es válido
        if i >= len(rows):
            break

        row = rows[i]

        # Localiza el <td> que quieres eliminar, si existe
        nested_tables = row.find_elements(By.XPATH, './/td/table')
        
        for nested_table in nested_tables:
            # Elimina el <td> anidado
            driver.execute_script("arguments[0].remove();", nested_table)

        # Ahora puedes obtener el texto del <td> que queda
        grupo = row.find_element(By.XPATH, './/td[2]').text.strip()
        boton = row.find_element(By.XPATH, './/td[10]/a')  # Elemento <a>

        data.append({
            'grupo': grupo,
            'link': {
                'texto': boton.text,
                'object': boton
            }
        })
    except Exception as e:
        print(f"Error al procesar la fila: {e}")

# Convierte a JSON
print(data)

# Cierra el navegador
driver.quit()
