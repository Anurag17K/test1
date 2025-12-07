pipeline {
    agent any

    tools {
        jdk 'Java-21'
    }

    environment {
        ACR_NAME         = 'acraktravelplanner01'
        IMAGE_NAME       = 'django-app'
        REGISTRY         = "${ACR_NAME}.azurecr.io"
        WEB_APP_NAME     = 'ak-travelplanner-cdso-dcr-01'
        RESOURCE_GROUP   = 'rg-ak-travelplanner-francecentral-dev-01'
        DOCKER_IMAGE_TAG = "latest"
        SONAR_TOKEN      = credentials('sonarcloud-token')
        AZURE_KEYVAULT_URL = 'https://akcdsotravelplannerkv01.vault.azure.net/'
        DJANGO_SETTINGS_MODULE = 'travelplanner.settings'
        CI = 'true'
    }

    stages {

        /* ---------------------------
         * Checkout
         * --------------------------- */
        stage('Checkout') {
            steps {
                git branch: 'main',
                    credentialsId: 'ff2fc462-fb36-4346-ae2b-684936782194',
                    url: 'https://github.com/Anurag17K/ak-cdso-travelplanner-01.git'
            }
        }

        stage('Check Java') {
            steps {
                sh 'java -version; echo $JAVA_HOME'
            }
        }

        /* ---------------------------
         * SonarCloud Analysis
         * --------------------------- */
        stage('SonarCloud Analysis') {
            steps {
                script {
                    withSonarQubeEnv('SonarCloud') {
                        sh '''
                        sonar-scanner \
                            -Dsonar.projectKey=Anurag17K_ak-cdso-travelplanner-01 \
                            -Dsonar.organization=anurag17k \
                            -Dsonar.sources=. \
                            -Dsonar.host.url=https://sonarcloud.io \
                            -Dsonar.login=$SONAR_TOKEN \
                            -Dsonar.python.coverage.reportPaths=coverage.xml
                        '''
                    }
                }
            }
        }

        /* ------------------------------------------------------
         * Run Quality Gate, Tests, and Deployment IN PARALLEL
         * ------------------------------------------------------ */
        stage('Post-Sonar Tasks (Parallel)') {
            parallel {

                /* ---------------------------
                 * NON-BLOCKING QUALITY GATE
                 * --------------------------- */
                stage('Quality Gate Check (Non-blocking)') {
                    steps {
                        echo "Starting Quality Gate check in background..."
                        timeout(time: 10, unit: 'MINUTES') {
                            waitForQualityGate abortPipeline: false
                        }
                        echo "Quality Gate check completed (pipeline continued regardless)."
                    }
                }

                /* ---------------------------
                 * Run Tests and Coverage (Non-blocking)
                 * --------------------------- */
                stage('Run Tests and Coverage (Non-blocking)') {
                    steps {
                        sh '''
                        docker build -t $REGISTRY/$IMAGE_NAME:$DOCKER_IMAGE_TAG .
                        docker run --rm \
                            --entrypoint "" \
                            -e DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE \
                            -e AZURE_KEYVAULT_URL=$AZURE_KEYVAULT_URL \
                            -e CI=true \
                            -v $WORKSPACE:/app \
                            $REGISTRY/$IMAGE_NAME:$DOCKER_IMAGE_TAG \
                            pytest trips/ --cov=trips --cov-report=xml:/app/coverage.xml -v
                        '''
                    }
                }

                /* ---------------------------
                 * BUILD & DEPLOY PIPELINE
                 * --------------------------- */
                stage('Build & Deploy') {
                    stages {

                        stage('Trivy Image Scan') {
                            steps {
                                sh '''
                                trivy image --severity HIGH,CRITICAL --exit-code 1 $REGISTRY/$IMAGE_NAME:$DOCKER_IMAGE_TAG || true
                                '''
                            }
                        }

                        stage('Login to Azure with Managed Identity') {
                            steps {
                                sh '''
                                az --version
                                az login --identity
                                '''
                            }
                        }

                        stage('Login to ACR') {
                            steps {
                                sh '''
                                az acr login --name $ACR_NAME
                                '''
                            }
                        }

                        stage('Push Docker Image to ACR') {
                            steps {
                                sh '''
                                docker push $REGISTRY/$IMAGE_NAME:$DOCKER_IMAGE_TAG
                                '''
                            }
                        }

                        stage('Deploy to Azure Web App') {
                            steps {
                                sh '''
                                az webapp config container set \
                                    --name $WEB_APP_NAME \
                                    --resource-group $RESOURCE_GROUP \
                                    --docker-custom-image-name $REGISTRY/$IMAGE_NAME:$DOCKER_IMAGE_TAG \
                                    --docker-registry-server-url https://$REGISTRY
                                '''
                            }
                        }
                    }
                }
            }
        }
    }

    post {
        success {
            echo "Deployment to Azure Web App successful!"
        }
        failure {
            echo "Deployment failed."
        }
    }
}
