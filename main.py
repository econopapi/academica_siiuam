import os
import sys
import time
import openpyxl
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

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
        self.default_timeout = 40

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
            WebDriverWait(self.driver, self.default_timeout).until(
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
            WebDriverWait(self.driver, self.default_timeout).until(
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
                "link_id": link.get_attribute("id"),
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

    def _create_course_directory(self, course_name):
        """
        Create a directory for the course if it doesn't exist
        
        :param course_name: Name of the course
        :return: Path to the created directory
        """
        # Sanitize course name to create a valid directory name
        sanitized_course_name = "".join(
            [c for c in course_name if c.isalnum() or c in (' ', '_', '-')]
        ).rstrip()
        
        course_dir = os.path.join(os.getcwd(), sanitized_course_name)
        os.makedirs(course_dir, exist_ok=True)
        return course_dir

    def scrape_all_groups(self, curso):
        """
        Scrape all groups for a course, saving each group to a separate Excel file
        
        :param curso: Course data
        """
        print(f"> [Accediendo a grupos para {curso['name_text']}]\n")

        # Re-fetch the course link right before clicking to avoid stale references.
        # Prefer link_id (stable within page load), then fallback to a tolerant text lookup.
        course_link_id = curso.get("link_id")
        course_name = " ".join(curso["name_text"].split())
        fallback_xpath = (
            "//table[@id='uent:E_UEA.PE02:AELCWBAWT011']"
            "//tr[@id]//a[.//span[contains(@id, 'NOM_OF_UEA_NO') and contains(normalize-space(), \"{}\")]]"
        ).format(course_name)

        clicked = False
        for attempt in range(3):
            try:
                if course_link_id:
                    locator = (By.ID, course_link_id)
                else:
                    locator = (By.XPATH, fallback_xpath)

                course_link = WebDriverWait(
                    self.driver,
                    25,
                    poll_frequency=0.5,
                    ignored_exceptions=(StaleElementReferenceException,),
                ).until(EC.element_to_be_clickable(locator))
                course_link.click()
                clicked = True
                break
            except (StaleElementReferenceException, TimeoutException):
                # If ID lookup fails, retry with tolerant text search.
                locator = (By.XPATH, fallback_xpath)
                try:
                    course_link = WebDriverWait(
                        self.driver,
                        25,
                        poll_frequency=0.5,
                        ignored_exceptions=(StaleElementReferenceException,),
                    ).until(EC.element_to_be_clickable(locator))
                    course_link.click()
                    clicked = True
                    break
                except (StaleElementReferenceException, TimeoutException):
                    pass

                if attempt < 2:
                    time.sleep(1)
                else:
                    raise

        if not clicked:
            print('Error localizando el enlace del curso')
            self.driver.quit()
            sys.exit(1)

        try:
            WebDriverWait(self.driver, 90).until(
                EC.presence_of_all_elements_located((By.ID, "uent:CURSOS.AE02:AELCWBAWT012")))
            print("> [Todos los grupos obtenidos]\n")
        except TimeoutException:
            print('Error cargando Módulos')
            self.driver.quit()
            sys.exit(1)

        # Create directory for course
        course_dir = self._create_course_directory(curso['name_text'])

        # Get groups
        grupos_data = self._extract_grupos_data()
        
        total_grupos = len(grupos_data)
        print(f"> [Total de grupos a procesar: {total_grupos}]\n")

        # Process all groups
        for idx, grupo_info in enumerate(grupos_data, start=1):
            self._scrape_group_data(grupo_info, course_dir, idx, total_grupos)

        print(f"> [Datos de todos los grupos guardados en {course_dir}]\n")

    def _extract_grupos_data(self):
        """
        Extract group data from table rows using browser-side JS to avoid stale row references.

        :return: List of group data
        """
        table_id = "uent:CURSOS.AE02:AELCWBAWT012"
        extractor_js = """
            const table = document.getElementById(arguments[0]);
            if (!table) return [];

            const rows = Array.from(table.querySelectorAll('tbody tr'));
            const data = [];

            for (const row of rows) {
                const cells = row.querySelectorAll('td');
                const grupo = cells[1] ? cells[1].innerText.trim() : '';
                const buttonAnchor = cells[9] ? cells[9].querySelector('a') : null;
                const buttonId = buttonAnchor ? buttonAnchor.id : null;

                if (grupo && buttonId) {
                    data.push({ grupo: grupo, boton_id: buttonId });
                }
            }

            return data;
        """

        for attempt in range(3):
            try:
                grupos_data = self.driver.execute_script(extractor_js, table_id)
                if grupos_data:
                    return grupos_data
                time.sleep(1)
            except StaleElementReferenceException:
                if attempt < 2:
                    time.sleep(1)
                else:
                    raise

        print("Error al extraer grupos: no se encontraron filas validas")
        self.driver.quit()
        sys.exit(1)

    def _scrape_group_data(self, grupo_info, course_dir, idx=None, total=None):
        """
        Scrape data for a specific group and save to an Excel file
        
        :param grupo_info: Dictionary with group information
        :param course_dir: Directory to save the group's Excel file
        :return: Filename of the saved Excel file
        """
        if idx is not None and total is not None:
            print(f"> [{time.strftime('%H:%M:%S')}] [Grupo {idx}/{total}] Accediendo a grupo {grupo_info['grupo']}\n")
        else:
            print(f"> [Accediendo a grupo {grupo_info['grupo']}]\n")
        
        # Click group button (re-find on each attempt to avoid stale references)
        clicked = False
        for attempt in range(3):
            try:
                boton = WebDriverWait(
                    self.driver,
                    20,
                    poll_frequency=0.5,
                    ignored_exceptions=(StaleElementReferenceException,),
                ).until(EC.element_to_be_clickable((By.ID, grupo_info['boton_id'])))
                boton.click()
                clicked = True
                break
            except (StaleElementReferenceException, TimeoutException):
                if attempt < 2:
                    time.sleep(1)
                else:
                    raise

        if not clicked:
            print(f"Error al acceder al grupo {grupo_info['grupo']}")
            self.driver.quit()
            sys.exit(1)

        try:
            time.sleep(2)
            WebDriverWait(self.driver, 90).until(
                EC.presence_of_all_elements_located((By.ID, "uent:ALUMNO_V_ACAD.AE02:AELCWBAWT013.1"))
            )
            table = self.driver.find_element(By.ID, 'uent:ALUMNO_V_ACAD.AE02:AELCWBAWT013.1')
            print(f"> [{time.strftime('%H:%M:%S')}] [Información de grupo cargada]\n")
        except TimeoutException:
            print('Error cargando lista de grupo')
            self.driver.quit()
            sys.exit(1)

        # Create Excel workbook for this group
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"Grupo {grupo_info['grupo']}"
        
        # Add headers
        ws.append(['numero_lista', 'matricula', 'nombre_alumno'])

        # Extract student data with JS to avoid stale row references after DOM refreshes.
        students_js = """
            const table = document.getElementById(arguments[0]);
            if (!table) return [];

            return Array.from(table.querySelectorAll('tbody tr'))
                .map((row) => {
                    const cells = row.querySelectorAll('td');
                    const numero = cells[0] ? cells[0].innerText.trim() : '';
                    const matricula = cells[1] ? cells[1].innerText.trim() : '';
                    const nombre = cells[2] ? cells[2].innerText.trim() : '';
                    return [numero, matricula, nombre];
                })
                .filter((item) => item[1] !== '' || item[2] !== '');
        """

        students_data = None
        for attempt in range(3):
            try:
                students_data = self.driver.execute_script(
                    students_js,
                    "uent:ALUMNO_V_ACAD.AE02:AELCWBAWT013.1",
                )
                if students_data is not None:
                    break
            except StaleElementReferenceException:
                if attempt < 2:
                    time.sleep(1)
                else:
                    raise

        if students_data is None:
            print(f"Error extrayendo alumnos del grupo {grupo_info['grupo']}")
            self.driver.quit()
            sys.exit(1)

        for numero, matricula, nombre in students_data:
            ws.append([numero, matricula, nombre])

        # Save Excel file. Some courses repeat group labels, so include index to avoid overwrite.
        if idx is not None:
            base_name = f"Grupo_{idx:03d}_{grupo_info['grupo']}"
        else:
            base_name = f"Grupo_{grupo_info['grupo']}"

        excel_filename = os.path.join(course_dir, f"{base_name}.xlsx")
        if os.path.exists(excel_filename):
            suffix = 2
            while True:
                candidate = os.path.join(course_dir, f"{base_name}__dup{suffix}.xlsx")
                if not os.path.exists(candidate):
                    excel_filename = candidate
                    break
                suffix += 1

        wb.save(excel_filename)
        if idx is not None and total is not None:
            print(
                f"> [{time.strftime('%H:%M:%S')}] [Grupo {idx}/{total}] Datos del grupo {grupo_info['grupo']} guardados en {excel_filename}\n"
            )
        else:
            print(f"> [Datos del grupo {grupo_info['grupo']} guardados en {excel_filename}]\n")

        # Return to groups page
        regresar_boton = WebDriverWait(self.driver, 20).until(
            EC.element_to_be_clickable((By.ID, "ufld:CD_REGRESAR.CONTROLES.ED01:AELCWBAWT012.1"))
        )
        regresar_boton.click()

        try:
            time.sleep(2)
            WebDriverWait(self.driver, 90).until(
                EC.presence_of_all_elements_located((By.ID, "uent:CURSOS.AE02:AELCWBAWT012"))
            )
            if idx is not None and total is not None:
                print(f"> [{time.strftime('%H:%M:%S')}] [Grupo {idx}/{total}] Regreso a lista de grupos OK\n")
            else:
                print("> [Grupos obtenidos]\n")
        except TimeoutException:
            print('Error cargando Módulos')
            self.driver.quit()
            sys.exit(1)

        return excel_filename

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