# Arquitectura

El notebook materializa el dataset mediante DVC, registra experimentos en MLflow y publica un pipeline joblib nuevamente con DVC. CI recupera una versión exacta del champion antes de construir la imagen.

    DVC/S3 -> notebook + MLflow -> champion.joblib -> Docker -> ECR
                                                        |
                                                   Lambda/FastAPI
                                                        |
                                                   API Gateway
                                                        |
                                                   Next.js/Vercel

ECR almacena imágenes; Lambda las ejecuta. El modelo queda dentro de la imagen por digest y Lambda no necesita acceso al bucket DVC durante inferencia.

Terraform está dividido en bootstrap, foundation y service para evitar el ciclo entre el backend remoto, ECR y la imagen que Lambda necesita.
