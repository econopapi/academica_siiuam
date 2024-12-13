import os
import sys
import time
import openpyxl
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

class SIIAScraper:
    def __init__(self, headless=False):
        """
        Initialize the SIIA Scraper
        
        :param headless: Boolean to run Chrome in headless mode
        """
        # Load environment variables
        load_dotenv()

        # Setup Chrome options
        self.options = webdriver.ChromeOptions()
        if headless:
            self.options.add_argument("--headless")
            self.options.add_argument("--no-sandbox")
            self.options.add_argument("--disable-dev-shm-usage")

        # Initialize driver
        self.driver = webdriver.Chrome(options=self.options)
        
        # Set window size
        screen_width = self.driver.execute_script("return window.screen.availWidth")
        screen_height = self.driver.execute_script("return window.screen.availHeight")
        self.driver.set_window_size(screen_width // 2, screen_height)

    def login(self):
        """
        Log in to the SIIA system
        """
        print("> [Entrando a SIIA]\n")
        url = os.getenv('SIIA_XOC_URI')
        self.driver.get(url)
        print("> [Login de SIIA cargado]\n")

        # Find login fields
        username_input = self.driver.find_element(By.ID, "ufld:CD_USUARIO.CONTROLES.ED01:AELCWBAWS003.1")
        password_input = self.driver.find_element(By.ID, "ufld:CD_CONTRASENA.CONTROLES.ED01:AELCWBAWS003.1")

        username_input.send_keys(os.getenv('SIIA_USERNAME'))
        password_input.send_keys(os.getenv('SIIA_PASSWORD'))
        self.driver.find_element(By.ID, "ufld:CD_INGRESAR.CONTROLES.ED01:AELCWBAWS003.1").click()

        # Wait for successful login
        try:
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_all_elements_located((By.ID, "ufld:CD_SALIR.CONTROL.ED01:AELCWBAWT002.1")))
            print("> [Acceso a SIIA exitoso!]\n")
        except TimeoutException:
            print('Error al acceder a SIIA')
            self.driver.quit()
            sys.exit(1)

    def access_courses(self):
        """
        Access courses by coordination
        
        :return: List of available courses
        """
        print("> [Accediendo a CURSOS POR COORDINACIÓN]\n")
        self.driver.find_element(By.ID, "ufld:OPCION_WEB_DOC_DE.OPCION_WEB_DOCENCIA.RH02:AELCWBAWT002.5").click()

        try:
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_all_elements_located((By.ID, "uent:E_UEA.PE02:AELCWBAWT011")))
            print("> [Cursos obtenidos]\n")
        except TimeoutException:
            print('Error cargando "Cursos por coordinación"')
            self.driver.quit()
            sys.exit(1)

        # Get courses
        cursos_table = self.driver.find_element(By.ID, "uent:E_UEA.PE02:AELCWBAWT011")
        cursos_rows = cursos_table.find_elements(By.XPATH, ".//tr[@id]")
        
        cursos_data = []
        for row in cursos_rows:
            link = row.find_element(By.XPATH, ".//a")
            name = row.find_element(By.XPATH, ".//span[contains(@id, 'NOM_OF_UEA_NO')]")
            
            cursos_data.append({
                "link": link,
                "name_text": name.text
            })

        return cursos_data

    def list_and_select_course(self, cursos_data):
        """
        List and allow selection of a specific course
        
        :param cursos_data: List of courses
        :return: Selected course index
        """
        for curso in cursos_data:
            print(f"> [{cursos_data.index(curso)}] - {curso['name_text']}")

        while True:
            try:
                uea_selected = int(input("\nSeleccione UEA a extraer > "))
                if 0 <= uea_selected < len(cursos_data):
                    return uea_selected
                else:
                    print("Selección fuera de rango. Intente de nuevo.")
            except ValueError:
                print("Por favor, ingrese un número válido.")


    def scrape_all_groups(self, curso):
        """
        Scrape all modules for a course
        
        :param curso: Course data
        :param selected_index: Index of the selected course
        """
        print(f"> [Accediendo a grupos para {curso['name_text']}]\n")
        curso['link'].click()

        try:
            WebDriverWait(self.driver, 60).until(
                EC.presence_of_all_elements_located((By.ID, "uent:CURSOS.AE02:AELCWBAWT012")))
            print("> [Todos los grupos obtenidos]\n")
        except TimeoutException:
            print('Error cargando Módulos')
            self.driver.quit()
            sys.exit(1)

        # Prepare Excel workbook
        wb = openpyxl.Workbook()
        
        # Get groups
        grupos_table = self.driver.find_element(By.ID, "uent:CURSOS.AE02:AELCWBAWT012")
        grupos_rows = grupos_table.find_elements(By.XPATH, ".//tbody/tr")
        
        grupos_data = self._extract_grupos_data(grupos_rows)
        
        # Process all groups
        for i in grupos_data:
            self._scrape_group_data(i, wb)

        # Remove default sheet and save
        wb.remove(wb['Sheet'])
        excel_filename = f'{curso["name_text"]}_todos_grupos.xlsx'
        wb.save(excel_filename)
        print(f"> [Datos de todos los grupos guardados en {excel_filename}]\n")

    def _extract_grupos_data(self, grupos_rows):
        """
        Extract group data from rows
        
        :param grupos_rows: Selenium WebElements of group rows
        :return: List of group data
        """
        grupos_data = []
        for row in grupos_rows:
            try:
                # Remove nested tables
                nested_tables = row.find_elements(By.XPATH, './/td/table')
                for nested_table in nested_tables:
                    self.driver.execute_script("arguments[0].remove();", nested_table)

                grupo = row.find_element(By.XPATH, './/td[2]').text.strip()
                boton = row.find_element(By.XPATH, './/td[10]/a')

                grupos_data.append({
                    'grupo': grupo,
                    'boton_id': boton.get_attribute("id")
                })
            except Exception as e:
                print(f"Error al procesar la fila: {e}")
        
        return grupos_data

    def _scrape_group_data(self, grupo_info, wb):
        """
        Scrape data for a specific group
        
        :param grupo_info: Dictionary with group information
        :param wb: Openpyxl workbook
        :return: Worksheet with group data
        """
        print(f"> [Accediendo a grupo {grupo_info['grupo']}]\n")
        
        # Click group button
        boton = self.driver.find_element(By.ID, grupo_info['boton_id'])
        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, grupo_info['boton_id'])))
        boton.click()

        try:
            time.sleep(2)
            WebDriverWait(self.driver, 60).until(
                EC.presence_of_all_elements_located((By.ID, "uent:ALUMNO_V_ACAD.AE02:AELCWBAWT013.1"))
            )
            table = self.driver.find_element(By.ID, 'uent:ALUMNO_V_ACAD.AE02:AELCWBAWT013.1')
            print("> [Información de grupo cargada]\n")
        except TimeoutException:
            print('Error cargando lista de grupo')
            self.driver.quit()
            sys.exit(1)

        # Create worksheet
        ws = wb.create_sheet(title=f"Grupo {grupo_info['grupo']}")
        ws.append(['Número', 'Matrícula', 'Nombre'])
        
        # Extract student data
        rows = table.find_elements(By.XPATH, ".//tbody/tr")
        for row in rows:
            numero = row.find_element(By.XPATH, "./td[1]/span").text
            matricula = row.find_element(By.XPATH, "./td[2]/span").text
            nombre = row.find_element(By.XPATH, "./td[3]/span").text
            
            ws.append([numero, matricula, nombre])

        # Return to groups page
        regresar_boton = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.ID, "ufld:CD_REGRESAR.CONTROLES.ED01:AELCWBAWT012.1"))
        )
        regresar_boton.click()

        try:
            time.sleep(2)
            WebDriverWait(self.driver, 60).until(
                EC.presence_of_all_elements_located((By.ID, "uent:CURSOS.AE02:AELCWBAWT012"))
            )
            print("> [Grupos obtenidos]\n")
        except TimeoutException:
            print('Error cargando Módulos')
            self.driver.quit()
            sys.exit(1)

        return ws

    def run(self):
        """
        Main method to run the scraper
        """
        try:
            # Login process
            self.login()

            # Get courses
            cursos_data = self.access_courses()

            # Select course
            selected_index = self.list_and_select_course(cursos_data)
            
            self.scrape_all_groups(cursos_data[selected_index])


        finally:
            # Always close the browser
            self.driver.quit()

def main():
    print("""
>>>[ACADEMICA SIIA EXTRACTOR]
Integración con SIIA - UAM.

WebScraper para la extracción de datos del
Sistema Integral de Información Académica
de la UAM Xochimilco.

Autor: Daniel Limón
Email: dani@dlimon.net
""")
    
    scraper = SIIAScraper()
    scraper.run()

if __name__ == "__main__":
    main()