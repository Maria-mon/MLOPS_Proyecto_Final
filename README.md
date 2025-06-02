Proyecto final
============

Integrantes:

 Maria del Mar Montenegro Mafla

Andrés Gómez

Juan Felipe Forero Bocanegra

Introducción
============

El presente informe documenta el desarrollo e implementación de un sistema completo de operaciones de Machine Learning (MLOps), como proyecto final de la asignatura Machine Learning Operations de la Maestría en Inteligencia Artificial de la Pontificia Universidad Javeriana. El objetivo central fue diseñar, construir y desplegar una arquitectura automatizada que permitiera gestionar el ciclo de vida de modelos de aprendizaje automático de forma reproducible, escalable y monitoreable.

El sistema integra múltiples componentes: recolección de datos vía Airflow, entrenamiento y versionamiento de modelos con MLflow, almacenamiento de artefactos en MinIO, exposición de modelos mediante una API en FastAPI, visualización a través de Streamlit, y monitoreo con Prometheus y Grafana. El despliegue de todos estos servicios se realizó mediante contenedores Docker orquestados sobre Kubernetes, utilizando Argo CD para la entrega continua y GitHub Actions para la integración continua.

A lo largo del informe se describen las decisiones de diseño, configuraciones técnicas, código fuente clave y flujos automatizados que permiten garantizar que los modelos desplegados sean actualizables, trazables y explicables, cumpliendo con las buenas prácticas de MLOps modernas.

Los datos fueron recopilados de un sitio web de listados de bienes raíces llamado Realtor operado por Move Inc. El objetivo es determinar el precio de una propiedad teniendo en cuenta el resto de características de la misma. A continuación, se da una descripción detallada de la implementación del sistema con sus correspondientes funcionalidades.

Descripción de la arquitectura
==============================

### Construcción de imagen personalizada de Airflow

Se construyó una imagen personalizada basada en apache/airflow:2.8.1 con el objetivo de adaptar el entorno de ejecución a los requerimientos específicos del proyecto. Esta imagen sirve como base para los servicios de orquestación definidos en Docker Compose.

Detalles de la construcción:

*   Usuario y directorio de trabajo:  
    Se establece el usuario airflow como contexto de ejecución y se define /home/airflow como directorio de trabajo.
*   Instalación de dependencias:  
    Se copia el archivo requirements.txt y se instalan las dependencias listadas utilizando pip, de forma local para el usuario (\--user), asegurando un entorno limpio y aislado.  
    
*   Estructura de logs:  
    Se crean directorios personalizados para almacenar los logs generados por los distintos componentes de Airflow (scheduler, webserver, task, dag\_processor\_manager). Esto permite mantener organizada la información y facilita el monitoreo.  
    
*   Configuración de logs:  
    Se define la variable de entorno AIRFLOW\_\_LOGGING\_\_BASE\_LOG\_FOLDER apuntando a la ruta personalizada /home/airflow/logs, lo que asegura que los logs sean escritos en el volumen persistente.  
    
*   Ejecución del servicio:  
    El comando (CMD) no se define en el Dockerfile, ya que será proporcionado por docker-compose.yml en cada servicio (webserver o scheduler), lo que permite reutilizar la misma imagen para ambos componentes.

Para garantizar la correcta ejecución de los DAGs y la integración con los distintos servicios del ecosistema MLOps, se definió un archivo requirements.txt con las siguientes dependencias:

*   apache-airflow==2.8.1: Plataforma base para la orquestación de flujos de trabajo.  
    
*   requests: Librería para realizar solicitudes HTTP, utilizada para la recolección de datos desde APIs externas.  
    
*   mlflow: Framework de seguimiento y gestión de experimentos y modelos.  
    
*   boto3: Cliente de AWS SDK para Python, usado para interactuar con MinIO como almacenamiento de artefactos.  
      
    
*   psycopg2-binary: Driver PostgreSQL para establecer conexión con la base de datos relacional utilizada por Airflow y MLflow.

Estas dependencias son instaladas dentro de la imagen personalizada de Airflow, asegurando un entorno reproducible y coherente con las necesidades del presente trabajo.

### Orquestación de Airflow con Docker Compose

Para la orquestación del componente Airflow, se definió un entorno distribuido mediante docker-compose, compuesto por dos servicios principales: el Webserver y el Scheduler, basados en una imagen personalizada construida desde la imagen oficial de Apache Airflow 2.8.1.

Ambos servicios se despliegan dentro de una red interna denominada mlops\_network, que garantiza la comunicación entre contenedores. A continuación, se describen sus características:

Airflow Webserver

*   Imagen personalizada: construida desde el directorio ./airflow, incluye instalación de dependencias vía requirements.txt.  
    
*   Variables de entorno:  
    

*   Configuración del LocalExecutor.  
    
*   Conexión con la base de datos PostgreSQL (fuera del contenedor) a través de la IP 172.17.0.1:30432.  
    
*   Integración con MLflow y MinIO como sistemas de seguimiento y almacenamiento de artefactos, respectivamente.  
    

*   Volúmenes montados:  
    

*   dags: definición de flujos de trabajo.  
    
*   logs: almacenamiento de logs internos.  
    
*   datasets y models: insumos y salidas del proceso de entrenamiento.  
    

*   Exposición de puerto: el servicio es accesible localmente a través del puerto 8081.  
    
*   Comando ejecutado: inicia el servidor web de Airflow (airflow webserver).  
    

Airflow Scheduler

*   Comparte la misma imagen y configuración que el webserver.  
    
*   Encargado de planificar y ejecutar tareas definidas en los DAGs.  
    
*   Ejecuta el comando airflow scheduler.  
    

Esta estructura permite separar responsabilidades y escalar los componentes de forma independiente si fuera necesario. Además, el uso de variables de entorno facilita la integración con herramientas externas como MLflow, PostgreSQL y MinIO, habilitando un entorno completo de MLOps.

### Gestión declarativa de recursos con Kustomize

Para facilitar la administración, reutilización y despliegue coherente de múltiples recursos de Kubernetes, se utilizó Kustomize. Esta permite agrupar, parametrizar y versionar los manifiestos YAML, manteniendo la trazabilidad y consistencia del entorno.

Kustomization.yaml

Se definió un archivo raíz kustomization.yaml con los siguientes elementos:

*   namespace: Todos los recursos son desplegados en el espacio de nombres mlops, asegurando su aislamiento lógico dentro del clúster.  
    
*   resources: Se listan explícitamente los manifiestos individuales que componen la arquitectura completa:  
    

*   postgres-deployment.yaml: base de datos relacional utilizada por Airflow y MLflow.  
    
*   minio.yaml: almacenamiento compatible con S3 para artefactos.  
    
*   mlflow.yaml: gestión y seguimiento de experimentos.  
    
*   api.yaml: API de inferencia desarrollada con FastAPI.  
    
*   streamlit\_ui.yaml: interfaz gráfica en Streamlit.  
    
*   prometheus.yaml: recolección de métricas.  
    
*   grafana.yaml: visualización y monitoreo del sistema.  
    

Esta organización modular permite aplicar todos los recursos simultáneamente con un solo comando (kubectl apply -k .) y facilita su mantenimiento y despliegue en otros entornos, como desarrollo, pruebas o producción, simplemente modificando capas (overlays) según sea necesario.

### Construcción de imagen personalizada de MLflow

Con el objetivo de adaptar MLflow a los requerimientos específicos del proyecto, se construyó una imagen personalizada basada en python:3.10-slim, la cual permite un entorno más liviano y controlado. Esta imagen es utilizada en el despliegue del servicio de MLflow dentro del clúster Kubernetes.

Detalles de construcción:

*   Sistema base: python:3.10-slim, una imagen optimizada que reduce el tamaño sin sacrificar compatibilidad.  
    
*   Dependencias del sistema:  
    Se instalan paquetes esenciales para compilar e integrar extensiones de Python, incluyendo:  
    

*   build-essential, curl, libpq-dev (necesario para conectarse a PostgreSQL).

*   Dependencias de Python:  
    A través del archivo requirements.txt se instalan las librerías principales requeridas para la ejecución de MLflow, incluyendo:

*   mlflow, psycopg2-binary (conexión a PostgreSQL), boto3 (conexión a MinIO/S3).

*   Puerto expuesto:  
    Se expone el puerto 5000, correspondiente al servidor de MLflow.  
    
*   Comando de ejecución:  
    El contenedor lanza el servidor MLflow configurado para:  
    

*   Usar una base de datos PostgreSQL como backend (mlflow\_db).  
    
*   Almacenar artefactos en un bucket remoto accesible vía s3://mlflow-artifacts.  
    
*   Escuchar conexiones entrantes desde cualquier IP (\--host 0.0.0.0).  
    

Esta imagen proporciona un entorno limpio y reproducible para el despliegue de MLflow, lo cual facilita su integración con otros componentes como Airflow, FastAPI y la interfaz gráfica en Streamlit.

### Despliegue de MLflow en Kubernetes

Para la gestión y seguimiento de los experimentos de aprendizaje automático, se desplegó MLflow en el clúster de Kubernetes utilizando un manifiesto compuesto por un recurso Deployment y un Service.

 1\. Deployment (mlflow)

Se utilizó la imagen personalizada mariamon/mlflow:latest, la cual ejecuta el servidor de MLflow mediante un comando explícito que establece:

*   URI del backend: una conexión a PostgreSQL (mlflow\_db) para almacenar los metadatos.  
    
*   Ruta raíz de artefactos: un bucket en MinIO (s3://mlflow-artifacts).  
    
*   Puerto y host de escucha: 0.0.0.0:5000, lo que permite recibir conexiones desde cualquier dirección.  
    

Además, se establecen variables de entorno necesarias para la autenticación en MinIO:

*   AWS\_ACCESS\_KEY\_ID: minioadmin  
    
*   AWS\_SECRET\_ACCESS\_KEY: minioadmin  
    
*   MLFLOW\_S3\_ENDPOINT\_URL: [](https://www.google.com/url?q=http://minio:9000&sa=D&source=editors&ust=1748888304730818&usg=AOvVaw3bRhJDSxw3qBqJhrjDmBOC)[http://minio:9000  
    ](https://www.google.com/url?q=http://minio:9000&sa=D&source=editors&ust=1748888304730927&usg=AOvVaw11ZbRkN06Cb_aAneASFXEi)

#### 2\. Service (mlflow)

El servicio se expone mediante NodePort en el puerto 30500, lo cual permite que otros contenedores y servicios (como Airflow o Streamlit) puedan comunicarse directamente con el servidor de MLflow para registrar y consultar experimentos y modelos.

Esta configuración garantiza que MLflow funcione como núcleo de trazabilidad y control de versiones de los modelos dentro del flujo de MLOps.

### Automatización del ciclo CI/CD con GitHub Actions: MLflow

Como parte del enfoque de integración y entrega continua (CI/CD), se implementó un workflow de GitHub Actions que automatiza el proceso de construcción, publicación y despliegue de la imagen Docker del componente MLflow, así como la actualización del manifiesto correspondiente.

#### Desencadenador:

El workflow se activa automáticamente cuando se detectan cambios en:

*   Cualquier archivo dentro de la carpeta mlflow/  
    
*   El archivo del workflow .github/workflows/build-mlflow.yml  
    

#### Flujo de trabajo:

1.  Checkout del repositorio  
    

*   Utiliza actions/checkout@v3 para obtener el código actualizado.

2.  Login en DockerHub  
    

*   Se autentica mediante credenciales almacenadas como secretos (DOCKER\_USERNAME y DOCKER\_PASSWORD) para poder subir imágenes.  
    

3.  Construcción y publicación de imagen  
    

*   Se construye la imagen Docker desde el directorio mlflow/, usando el sha del commit como etiqueta.
*   La imagen es publicada en DockerHub bajo el nombre mariamon/mlflow:<sha>.  
    

4.  Actualización del manifiesto de Kubernetes  
    

*   El archivo manifests/mlflow.yaml se modifica automáticamente para referenciar la nueva etiqueta de imagen, reemplazando la línea:  
      
    image: mariamon/mlflow:...

con:

            image: mariamon/mlflow:<sha>

        5.  Commit y push del manifiesto actualizado

*   Si hubo cambios, el archivo modificado se hace commit y push automáticamente al repositorio usando un token personal (GH\_TOKEN\_PUSH), manteniendo sincronizado el manifiesto para que Argo CD lo detecte y realice el despliegue actualizado.

#### Beneficios:

*   Garantiza que cada cambio en el código de MLflow se refleje en una nueva imagen versionada.  
    
*   El sistema se mantiene siempre actualizado sin intervención manual.  
    
*   Se acopla perfectamente con Argo CD para un flujo GitOps completo.  
    

Este mecanismo asegura consistencia, reproducibilidad y trazabilidad en la entrega del servicio de MLflow.

### Despliegue de PostgreSQL en Kubernetes

Como parte de la infraestructura, se desplegó un servicio de base de datos PostgreSQL en el clúster de Kubernetes, el cual es utilizado tanto por Airflow como por MLflow para el manejo de metadatos. Este despliegue está compuesto por tres recursos:

#### 1\. PersistentVolumeClaim (postgres-pvc)

Se crea un volumen persistente de 2 GiB de capacidad con modo de acceso ReadWriteOnce, lo que garantiza que los datos almacenados por PostgreSQL permanezcan disponibles incluso ante reinicios del contenedor.

#### 2\. Deployment (postgres)

Se define un despliegue de una réplica del contenedor oficial postgres:13. Se configuran las siguientes variables de entorno:

*   POSTGRES\_DB=airflow  
    
*   POSTGRES\_USER=airflow  
    
*   POSTGRES\_PASSWORD=airflow  
    

El almacenamiento de datos se realiza en el volumen montado en /var/lib/postgresql/data, enlazado al PersistentVolumeClaim previamente creado.

#### 3\. Service (postgres)

Se expone el servicio mediante un NodePort en el puerto 30432, permitiendo el acceso desde otros contenedores del clúster y desde fuera de este, facilitando la conexión desde Airflow, MLflow y cualquier otro componente que requiera persistencia de datos estructurados.

Esta configuración asegura la disponibilidad y escalabilidad del componente de base de datos, clave en el seguimiento de experimentos y ejecución de DAGs.

### Despliegue de MinIO en Kubernetes

Para la gestión y almacenamiento de artefactos generados por MLflow, se desplegó MinIO, una solución de almacenamiento compatible con S3, dentro del clúster de Kubernetes. Este componente actúa como repositorio de modelos entrenados y otros elementos relevantes del ciclo de vida del aprendizaje automático.

#### 1\. PersistentVolumeClaim (minio-pvc)

Se crea un volumen persistente de 2 GiB con acceso ReadWriteOnce, asegurando la persistencia de los datos aún en caso de reinicios del contenedor.

#### 2\. Deployment (minio)

Se despliega una instancia del contenedor oficial minio/minio:latest, configurada con:

*   Ruta de almacenamiento: /data, montada sobre el volumen persistente.  
    
*   Interfaz de administración web: habilitada mediante \--console-address :9001.  
    
*   Credenciales de acceso:  
    

*   Usuario: minioadmin  
    
*   Contraseña: minioadmin  
    

El contenedor expone los puertos 9000 (API S3) y 9001 (consola web).

#### 3\. Service (minio-nodeport)

Se expone MinIO a través de un servicio tipo NodePort para acceso desde el exterior del clúster:

*   Puerto 30900: API S3 (http://<node-ip>:30900)  
    
*   Puerto 30901: Consola web (http://<node-ip>:30901)  
    

Esta configuración permite que MLflow pueda almacenar y consultar artefactos en MinIO como si se tratara de un bucket de S3, manteniendo compatibilidad con la arquitectura de almacenamiento definida.

### Construcción de imagen personalizada para el API de Inferencia

Para desplegar el servicio de inferencia, se construyó una imagen personalizada basada en python:3.9. Esta contiene una aplicación desarrollada en FastAPI que permite consumir el mejor modelo registrado en MLflow y exponer un endpoint de predicción REST.

#### Detalles de construcción:

*   Imagen base: python:3.9, que ofrece compatibilidad con las principales librerías de ciencia de datos y frameworks web modernos.  
    
*   Directorio de trabajo: /app, donde se copian y ejecutan todos los archivos necesarios para el funcionamiento del servicio.  
    
*   Instalación de dependencias:  
    Se copia el archivo requirements.txt y se instalan las librerías necesarias para la aplicación, entre ellas: fastapi, uvicorn, mlflow, boto3, y scikit-learn.  
    
*   Copia del código fuente:  
    Se copian todos los archivos de la aplicación al contenedor.  
    
*   Comando de ejecución:  
    Se ejecuta el servidor uvicorn sobre el archivo main.py, exponiendo la API en el puerto 8000.  
    

Esta imagen es construida automáticamente mediante GitHub Actions y desplegada en el clúster Kubernetes. Al estar desacoplada del entorno de entrenamiento, garantiza que los modelos puedan actualizarse en MLflow sin necesidad de modificar el código fuente.

### Despliegue del API de Inferencia con FastAPI

Para exponer el modelo en producción y permitir predicciones en tiempo real, se construyó y desplegó una API utilizando FastAPI, ejecutada dentro del clúster de Kubernetes como un microservicio independiente. Esta API consume el mejor modelo registrado en MLflow y ofrece un endpoint de inferencia accesible desde el exterior.

#### 1\. Deployment (inference-api)

Se despliega el contenedor mariamon/inference-api:latest, el cual es construido automáticamente mediante GitHub Actions cada vez que se actualiza el repositorio. Este contenedor ejecuta la API con uvicorn sobre el puerto 8000.

El servicio está configurado con las siguientes variables de entorno:

*   MLflow:  
    

*   MLFLOW\_TRACKING\_URI: URL del servidor de MLflow dentro del clúster.  
    
*   MODEL\_NAME: nombre del modelo a consumir desde el registro de modelos.  
    

*   MinIO (artefactos):  
    

*   MLFLOW\_S3\_ENDPOINT\_URL, AWS\_ACCESS\_KEY\_ID, AWS\_SECRET\_ACCESS\_KEY.  
    

*   Airflow (conectividad de base de datos):  
    

*   AIRFLOW\_CONN\_POSTGRES\_DEFAULT: conexión para registrar inferencias si se desea integrarlo en un DAG.  
    

#### 2\. Service (inference-api)

Se expone el API mediante un servicio tipo NodePort en el puerto 30800, lo que permite recibir solicitudes desde clientes externos al clúster en la dirección:  
http://<node-ip>:30800.

Esta arquitectura desacoplada permite que el modelo en producción se actualice automáticamente sin necesidad de modificar el código fuente, siempre y cuando se actualice el modelo en MLflow con el mismo MODEL\_NAME bajo la etapa “Production”.

### Automatización del ciclo CI/CD con GitHub Actions: API de Inferencia

Se implementó un segundo flujo de trabajo en GitHub Actions para automatizar la construcción, publicación y actualización de la imagen Docker de la API de inferencia basada en FastAPI, así como la sincronización automática del manifiesto asociado.

#### Desencadenador:

El workflow se activa cada vez que se detectan cambios en:

*   Cualquier archivo dentro del directorio api/  
    
*   El archivo del workflow .github/workflows/build-api.yml  
    

#### Flujo de trabajo:

1.  Clonación del repositorio  
    

*   Se obtiene la última versión del código fuente mediante actions/checkout@v3.  
    

2.  Autenticación en DockerHub  
    

*   Utiliza DOCKER\_USERNAME y DOCKER\_PASSWORD para iniciar sesión y poder publicar imágenes.

3.  Construcción y publicación de imagen Docker  
    

*   Se construye la imagen con el contenido de ./api y se etiqueta usando el hash del commit actual (github.sha).  
    
*   La imagen se publica en DockerHub bajo el nombre mariamon/inference-api:<sha>.  
    

4.  Actualización automática del manifiesto  
    

*   Se modifica el archivo manifests/api.yaml para reemplazar la línea que contiene:  
    image: mariamon/inference-api:...

por:

image: mariamon/inference-api:<sha>

     5. Commit y sincronización con el repositorio remoto

*   Si se detectan cambios, se realiza automáticamente un commit y se hace push a la rama main usando un token personal (GH\_TOKEN\_PUSH).  
    
*   Esto permite que Argo CD detecte el cambio y sincronice el entorno de Kubernetes con la nueva versión de la imagen.

#### Beneficios:

*   Automatiza completamente el ciclo de construcción y despliegue de la API.  
    
*   Evita errores manuales en la gestión de versiones.  
    
*   Mantiene el manifiesto actualizado y rastreable, integrando prácticas de GitOps con Argo CD.

Este pipeline fortalece la entrega continua del componente de inferencia, asegurando que cualquier actualización funcional se traduzca en un despliegue inmediato y controlado en producción.

### Construcción de imagen personalizada para la interfaz gráfica (Streamlit)

Con el fin de ofrecer una visualización sencilla y accesible de las predicciones y versiones de modelos, se desarrolló una aplicación en Streamlit contenida dentro de una imagen Docker personalizada. Esta interfaz permite al usuario realizar inferencias, visualizar resultados y explorar el historial de modelos registrados en MLflow.

#### Detalles de construcción:

*   Imagen base: python:3.9, compatible con Streamlit y las bibliotecas requeridas.  
    
*   Directorio de trabajo: /app, donde se instala la aplicación.  
    
*   Instalación de dependencias:  
    Se copian e instalan las librerías listadas en requirements.txt, que incluyen streamlit, mlflow, pandas, boto3, entre otras necesarias para la conectividad y visualización.  
    
*   Aplicación principal:  
    El archivo app.py contiene la lógica de la interfaz, permitiendo ingresar datos, consultar inferencias, comparar métricas y visualizar explicaciones de modelos.
*   Comando de ejecución:  
    Se lanza el servidor de Streamlit escuchando en el puerto 8501 y accesible desde cualquier dirección (0.0.0.0), permitiendo el acceso externo al servicio desplegado en Kubernetes.  
    

Esta imagen se construye automáticamente mediante GitHub Actions y se despliega como un microservicio independiente, consumiendo la API de inferencia para mostrar los resultados en una interfaz amigable para el usuario final.

### Despliegue de la interfaz gráfica con Streamlit

Para ofrecer una interfaz visual accesible que facilite la interacción con el modelo en producción, se desplegó la aplicación dentro del clúster de Kubernetes. Esta interfaz permite a los usuarios ingresar datos, consultar predicciones y visualizar el historial de modelos registrados en MLflow.

#### 1\. Deployment (streamlit-ui)

Se desplegó el contenedor mariamon/streamlit-ui:latest, generado automáticamente mediante GitHub Actions. El contenedor expone el puerto 8501, correspondiente al servidor web de Streamlit.

El contenedor está configurado con la variable de entorno:

*   INFERENCE\_API\_URL: URL del servicio de inferencia (http://inference-api:8000/predict), lo cual permite conectar directamente con el modelo desplegado para realizar predicciones.  
    

#### 2\. Service (streamlit-ui)

El servicio se expone mediante un NodePort accesible desde el exterior del clúster en el puerto 30701, lo que permite ingresar a la aplicación desde un navegador mediante la URL:  
http://<node-ip>:30701.

Esta interfaz proporciona una experiencia de usuario directa, simplificando el consumo del modelo desplegado sin necesidad de conocimientos técnicos o uso de herramientas adicionales como Postman o cURL.

### Automatización del ciclo CI/CD con GitHub Actions: Interfaz Streamlit

Se implementó un flujo de trabajo adicional de GitHub Actions que automatiza el ciclo de integración y entrega continua (CI/CD) de la interfaz gráfica. Este proceso garantiza que cualquier cambio realizado en el código fuente de la interfaz se vea reflejado automáticamente en producción sin intervención manual.

#### Desencadenador:

El workflow se ejecuta automáticamente cuando se detectan cambios en:

*   Archivos dentro del directorio streamlit\_ui/  
    
*   El archivo .github/workflows/build-streamlit-ui.yml  
    

#### Flujo de trabajo:

1.  Checkout del código  
    

*   Descarga el código actualizado desde el repositorio.  
    

2.  Login en DockerHub  
    

*   Utiliza DOCKER\_USERNAME y DOCKER\_PASSWORD para autenticarse y permitir la publicación de la imagen resultante.

3.  Construcción y publicación de la imagen Docker  
    

*   Se construye la imagen desde ./streamlit\_ui y se etiqueta con el hash del commit (IMAGE\_TAG).  
    
*   La imagen es publicada en DockerHub bajo el nombre mariamon/inference-ui:<sha>.  
    

4.  Actualización automática del manifiesto  
    

*   El archivo manifests/streamlit\_ui.yaml se edita para reflejar la nueva etiqueta de la imagen, asegurando que el manifiesto coincida con la versión recién publicada.

5.  Commit y sincronización  
    

*   Si hay cambios en el manifiesto, se realiza automáticamente un commit y se hace push a la rama main usando el token GH\_TOKEN\_PUSH.  
    

#### Resultado:

Este pipeline asegura que la interfaz Streamlit esté siempre actualizada con la última versión del código, y permite que Argo CD detecte el cambio y lo despliegue automáticamente en el clúster Kubernetes.

### Servicios expuestos mediante NodePort

Para permitir el acceso externo a los principales componentes del sistema desplegado en Kubernetes, se configuraron servicios de tipo NodePort para PostgreSQL, MLflow y MinIO. Estos servicios habilitan la interacción con cada microservicio desde fuera del clúster, facilitando el desarrollo, monitoreo y pruebas.

#### 1\. PostgreSQL (postgres-nodeport)

*   Puerto interno: 5432  
    
*   Puerto expuesto: 30432  
    Permite a Airflow, MLflow y otros servicios conectarse a la base de datos PostgreSQL desde fuera del clúster.  
    

#### 2\. MLflow (mlflow-nodeport)

*   Puerto interno: 5000  
    
*   Puerto expuesto: 30500  
    Habilita el acceso a la interfaz y API de MLflow, permitiendo registrar experimentos, consultar modelos y administrar su ciclo de vida.  
    

#### 3\. MinIO (minio-nodeport)

*   Puerto interno: 9000 (API S3 compatible)  
    
*   Puerto expuesto: 30900  
    Permite a MLflow y otros servicios interactuar con el almacenamiento de artefactos mediante el protocolo S3, emulado por MinIO.

Estos servicios son fundamentales para garantizar la conectividad entre los componentes del sistema y asegurar su correcta integración dentro del flujo de MLOps desplegado.

### Monitoreo con Prometheus

Como parte del sistema de observabilidad, se desplegó Prometheus dentro del clúster de Kubernetes para recolectar métricas operativas y de uso del API de inferencia. Este componente permite monitorear el estado del servicio en tiempo real, facilitando la identificación de cuellos de botella o caídas en la disponibilidad.

#### 1\. ConfigMap (prometheus-config)

Se define un archivo de configuración personalizado (prometheus.yml) mediante un ConfigMap, en el que se especifica un job llamado inference-api con una frecuencia de sondeo de 5 segundos. Prometheus recolecta métricas expuestas por la API de inferencia en el puerto 8000.

#### 2\. Deployment (prometheus)

El contenedor prom/prometheus:latest se lanza con la configuración montada desde el ConfigMap. La aplicación escucha en el puerto 9090 y monta el archivo prometheus.yml en la ruta esperada por el sistema (/etc/prometheus/).

#### 3\. Service (prometheus)

Se expone Prometheus mediante un servicio tipo NodePort en el puerto 30990, lo que permite el acceso al panel de monitoreo desde un navegador mediante:  
http://<node-ip>:30990.

Este servicio es clave para asegurar la disponibilidad del sistema y observar el comportamiento de la API de inferencia a lo largo del tiempo.

### Visualización de métricas con Grafana

Complementando la recolección de métricas mediante Prometheus, se desplegó Grafana en el clúster de Kubernetes para ofrecer una visualización gráfica y configurable del comportamiento del entorno. Esta integración permite observar en tiempo real el estado de los servicios desplegados, facilitando la supervisión de la API de inferencia.

#### 1\. Deployment (grafana)

Se despliega una instancia del contenedor oficial grafana/grafana:latest, que expone su interfaz web en el puerto 3000. A través de esta, se pueden crear dashboards personalizados, establecer alertas y conectar múltiples fuentes de datos, entre ellas Prometheus.

#### 2\. Service (grafana)

Grafana se expone mediante un NodePort, accesible en el puerto 30930, lo que permite su visualización desde cualquier navegador externo al clúster en la URL:  
http://<node-ip>:30930.

#### 3\. Integración con Prometheus

Una vez desplegado, se configura Prometheus como fuente de datos dentro de Grafana. Esto habilita la visualización de métricas recolectadas por Prometheus, tales como número de peticiones, tiempos de respuesta, estado del servicio de inferencia, entre otras.

Este conjunto de herramientas de observabilidad permite mantener control sobre el desempeño y la estabilidad de los microservicios desplegados, siguiendo buenas prácticas de MLOps.

### Despliegue automatizado con Argo CD

Para la implementación del enfoque GitOps y facilitar el despliegue automatizado de todos los componentes del sistema, se utilizó Argo CD, una herramienta de entrega continua declarativa para Kubernetes.

#### Manifiesto de aplicación (install.yaml)

Se definió una aplicación en Argo CD mediante un manifiesto tipo Application, el cual:

*   Nombre: mlops-proyecto-final  
    
*   Namespace de Argo CD: argocd (espacio de nombres donde está instalado Argo CD)
*   Repositorio fuente:  
    

*   repoURL: https://github.com/Maria-mon/MLOPS\_Proyecto\_Final  
    
*   targetRevision: rama main  
    
*   path: subcarpeta manifests, donde se ubican los archivos gestionados con Kustomize.  
    

*   Destino del despliegue:  
    

*   server: clúster Kubernetes por defecto (https://kubernetes.default.svc)  
    
*   namespace: mlops  
    

*   Política de sincronización automática:  
    

*   prune: true: elimina recursos obsoletos no presentes en el repositorio.  
    
*   selfHeal: true: repara desviaciones entre el estado real del clúster y el definido en Git.  
    
*   CreateNamespace=true: crea el namespace mlops si aún no existe.

Esta configuración permite que cualquier cambio en el repositorio se replique automáticamente en el clúster, asegurando que el estado deseado del sistema esté siempre sincronizado con la definición en Git, alineándose con las mejores prácticas de MLOps.

### Configuración de clúster local con Kind

Durante el desarrollo y validación del sistema, se utilizó Kind (Kubernetes IN Docker) para levantar un clúster local de Kubernetes. Esto permitió realizar pruebas completas del entorno de MLOps sin necesidad de utilizar una infraestructura en la nube, facilitando el ciclo de desarrollo continuo.

#### Archivo de configuración (kind-config.yaml)

El clúster está compuesto por un único nodo con rol de control-plane, y se definieron mapeos de puertos para permitir el acceso desde el host a los servicios internos desplegados:

*   30500: expone MLflow (http://localhost:30500)  
    
*   30432: expone PostgreSQL (localhost:30432)  
    
*   30900: expone MinIO (http://localhost:30900)  
    

Esta configuración permite interactuar con los servicios principales desde el entorno local, garantizando la funcionalidad del ciclo completo de entrenamiento, registro, despliegue y consumo de modelos en un entorno de pruebas realista.

Descripción de las funcionalidades
==================================

### Orquestación del pipeline de datos con Airflow

Como parte del ciclo automatizado de procesamiento y entrenamiento, se implementó un DAG (Directed Acyclic Graph) en Apache Airflow que permite orquestar la recolección y preprocesamiento de datos desde una API externa, integrando posteriormente los datos a una base de datos PostgreSQL.

#### DAG: get\_ingest\_preprocess

Este flujo consta de dos tareas principales:

#### 1\. get\_data\_from\_api

*   Realiza una solicitud GET a la API del curso (http://10.43.101.108:80/data) con parámetros de grupo y día.  
    
*   Procesa la estructura JSON anidada mediante pandas.json\_normalize.  
    
*   Detecta si la tabla raw\_data ya existe en PostgreSQL:

*   Si no existe, la crea automáticamente.  
    
*   Si existe, adapta el esquema agregando nuevas columnas y completando con valores nulos (NaN) si faltan.  
    

*   Convierte todos los datos a texto y guarda los registros en la tabla raw\_data.  
    

#### 2\. preprocess\_data

*   Carga los datos desde la tabla raw\_data.  
    
*   Realiza limpieza básica:  
    

*   Elimina duplicados.  
    
*   Convierte a tipo numérico las columnas price, bed, bath, acre lot y house size, forzando errores a NaN.  
    

*   Almacena el resultado en la tabla clean\_data, sobrescribiendo su contenido.  
    

#### Configuración técnica del DAG:

*   Nombre: get\_ingest\_preprocess  
    
*   Inicio: 1 de enero de 2024  
    
*   Frecuencia: ejecución manual (schedule\_interval=None)  
    
*   Dependencias: la tarea de preprocesamiento se ejecuta solo después de obtener y almacenar los datos.  
    

Este DAG automatiza el proceso de ETL, asegurando que los datos nuevos obtenidos de la API sean integrados y normalizados antes de ser utilizados en tareas de entrenamiento posteriores.

### Entrenamiento condicional y registro de modelos con Airflow y MLflow

Para automatizar la toma de decisiones sobre el reentrenamiento del modelo y su registro en MLflow, se desarrolló un segundo DAG de Airflow llamado evaluate\_and\_train. Este flujo permite evaluar si un nuevo conjunto de datos justifica el reentrenamiento, registrar métricas, comparar versiones y actualizar el modelo en producción si se observa una mejora significativa.

#### DAG: evaluate\_and\_train

Este DAG se ejecuta manualmente (@once) y contiene cuatro tareas secuenciales:

#### 1\. should\_train\_model

*   Carga los datos desde la tabla clean\_data.  
    
*   Evalúa condiciones mínimas para justificar el entrenamiento:  
    

*   Cantidad suficiente de registros (≥ 50).  
    
*   Variabilidad suficiente en la variable objetivo (price).  
    

*   La decisión se comunica a través de XComs. Si no se cumple, se omite el entrenamiento.  
    

#### 2\. train\_model

*   Si la decisión es entrenar, este bloque:  
    

*   Prepara las variables predictoras numéricas (X) y la variable objetivo (y).  
    
*   Entrena un modelo LinearRegression.  
    
*   Calcula el RMSE como métrica de desempeño.
*   Registra los parámetros, métrica y modelo en MLflow, asignando el nombre BestHousePriceModel.  
    

#### 3\. compare\_models

*   Compara el nuevo modelo con el modelo actualmente en producción (si existe).  
    
*   Si el nuevo modelo mejora el RMSE, se promueve automáticamente a la etapa de Production en MLflow.

#### 4\. log\_skipped\_reason

*   Si el entrenamiento fue omitido, esta tarea registra en MLflow el motivo del rechazo, utilizando un run especial llamado train\_skipped.  
    

#### Flujo condicional:

*   Si se cumple la condición para entrenar → se ejecutan train\_model y luego compare\_models.  
    
*   Si no se justifica entrenar → se ejecuta únicamente log\_skipped\_reason.  
    

Este DAG integra prácticas sólidas de MLOps: decisión basada en datos, entrenamiento automatizado, versionamiento de modelos y despliegue controlado, todo orquestado dentro del ecosistema de Airflow y MLflow.

### Detalle del código fuente de la API de inferencia

La implementación de la API de inferencia se desarrolló utilizando FastAPI, integrando múltiples funcionalidades en un único servicio:

*   Carga del modelo:  
    Utiliza mlflow.pyfunc.load\_model() para cargar dinámicamente el modelo registrado bajo el nombre BestHousePriceModel en etapa Production.  
    
*   Estandarización de entrada:  
    El JSON recibido por POST /predict es convertido a DataFrame. Se asegura que las columnas esperadas estén presentes, agregando NaN en caso de ausencia, y reordenando según el modelo.
*   Inferencia y logging:  
    Se realiza la predicción usando el modelo cargado. El resultado se almacena en la tabla inference\_log de PostgreSQL junto con los datos de entrada.
*   Monitoreo:  
    Se definen contadores de Prometheus para:  
    

*   Total de inferencias exitosas (inference\_requests\_total)  
    
*   Total de errores (inference\_errors\_total)  
    

*   Además, se expone el endpoint GET /metrics para que Prometheus pueda recolectar métricas automáticamente.

Este diseño permite mantener el sistema observables, trazable y alineado con prácticas modernas de puesta en producción.

### Interfaz gráfica de inferencia y visualización con Streamlit

Se desarrolló la interfaz con el propósito de facilitar la interacción con el modelo en producción, consultar el historial de ejecuciones en MLflow y proporcionar interpretabilidad de las predicciones mediante SHAP.

#### Características principales:

##### 1\. Inferencia vía API

*   Permite al usuario ingresar los parámetros requeridos por el modelo desde una barra lateral.  
    
*   Las columnas esperadas por el modelo se infieren dinámicamente. Para ello, la aplicación intenta ejecutar una predicción dummy con datos genéricos. Si se produce una excepción, se inspecciona el mensaje de error mediante expresiones regulares para extraer las variables requeridas en tiempo de entrenamiento. Esto asegura que los campos mostrados al usuario coincidan con los que el modelo necesita, incluso si cambian con una nueva versión.  
    
*   Si la inferencia de columnas falla, se aplica una configuración de respaldo con columnas estándar: group\_number, batch\_number, bed, bath. Al presionar el botón "Predecir", se envía una solicitud POST al endpoint de la API de inferencia desplegada en Kubernetes. Muestra el precio estimado de la vivienda en un mensaje destacado si la predicción es exitosa.

##### 2\. Historial de modelos en MLflow

*   Consulta automáticamente los registros del experimento en MLflow.  
    
*   Presenta una tabla con:  
    

*   Identificador del run  
    
*   Métrica RMSE  
    
*   Estado de ejecución  
    
*   Indicador de si el modelo está en producción  
    

*   Esta funcionalidad permite comparar distintas versiones y su rendimiento de manera sencilla.  
    

##### 3\. Explicabilidad con SHAP

*   Genera una visualización waterfall explicando la predicción actual con la librería SHAP.  Muestra el impacto de cada variable de entrada en la predicción final. Este componente refuerza la transparencia del modelo y facilita su comprensión por parte de usuarios no técnicos.

#### Integraciones clave:

*   MLflow: para carga del modelo y consulta del historial.  
    
*   FastAPI: para realizar predicciones vía API.  
    
*   Prometheus: para métricas de uso.  
    
*   SHAP: para interpretabilidad del modelo.  
    

Esta interfaz integra inferencia dinámica, trazabilidad, transparencia y facilidad de uso, alineándose con las mejores prácticas de MLOps para interfaces de usuario en producción Además, es fácilmente extensible y resulta útil tanto para usuarios técnicos como no técnicos, al combinar predicción, trazabilidad y explicabilidad de manera centralizada y accesible.

Conclusiones
============

El desarrollo del proyecto permitió consolidar los conocimientos adquiridos a lo largo del curso de Machine Learning Operations, integrando herramientas modernas en una arquitectura completa y funcional para el ciclo de vida de modelos de aprendizaje automático.

1.  Automatización y reproducibilidad: Se logró automatizar completamente el flujo de recolección, procesamiento, entrenamiento, evaluación y despliegue de modelos, garantizando la trazabilidad de cada versión y facilitando su mantenimiento.  
    
2.  Modularidad y escalabilidad: El uso de contenedores aislados para cada componente (Airflow, MLflow, MinIO, FastAPI, Streamlit, Prometheus, Grafana) permitió mantener una arquitectura modular y escalable, preparada para su evolución en entornos reales de producción.  
    
3.  Despliegue continuo con GitOps: La integración de GitHub Actions y Argo CD permitió implementar un enfoque GitOps, asegurando que cualquier cambio en el repositorio se refleje automáticamente en el clúster de Kubernetes, manteniendo sincronía entre código e infraestructura.  
    
4.  Interpretabilidad y monitoreo: La incorporación de explicabilidad con SHAP y monitoreo con Prometheus y Grafana refuerza la confiabilidad del sistema y aporta herramientas fundamentales para el diagnóstico y supervisión continua del modelo en producción.  
    
5.  Buena práctica en la toma de decisiones: Se implementaron mecanismos para decidir cuándo entrenar y promover un nuevo modelo con base en datos y métricas, evitando actualizaciones innecesarias y privilegiando versiones con mejoras comprobables.  
    

En resumen, el proyecto representa una solución de MLOps robusta, extensible y alineada con estándares actuales de la industria, que puede servir como base para sistemas reales en escenarios empresariales o institucionales.
