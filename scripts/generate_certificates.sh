#!/bin/bash

# Script para gerar certificados SSL para desenvolvimento do MindFlow
# Uso: ./scripts/generate_certificates.sh

set -e

CERT_DIR="certs"
CONFIG_FILE="$CERT_DIR/openssl.conf"

echo "🔐 Gerando certificados SSL para MindFlow gRPC..."

# Criar diretório de certificados
mkdir -p "$CERT_DIR"

# Criar configuração OpenSSL
cat > "$CONFIG_FILE" << EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = v3_req

[dn]
CN = localhost
O = MindFlow Development
OU = gRPC Service

[v3_req]
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = 127.0.0.1
IP.1 = 127.0.0.1
IP.2 = 0.0.0.0
EOF

# Gerar chave privada CA
echo "📝 Gerando chave privada CA..."
openssl genrsa -out "$CERT_DIR/ca.key" 2048

# Gerar certificado CA
echo "📜 Gerando certificado CA..."
openssl req -new -x509 -days 365 -key "$CERT_DIR/ca.key" -out "$CERT_DIR/ca.crt" -subj "/CN=MindFlow-Dev-CA/O=Development/C=BR"

# Gerar chave privada do servidor
echo "🔑 Gerando chave privada do servidor..."
openssl genrsa -out "$CERT_DIR/server.key" 2048

# Gerar CSR do servidor
echo "📋 Gerando CSR do servidor..."
openssl req -new -key "$CERT_DIR/server.key" -out "$CERT_DIR/server.csr" -config "$CONFIG_FILE"

# Assinar certificado do servidor
echo "✍️ Assinando certificado do servidor..."
openssl x509 -req -in "$CERT_DIR/server.csr" -CA "$CERT_DIR/ca.crt" -CAkey "$CERT_DIR/ca.key" -CAcreateserial -out "$CERT_DIR/server.crt" -days 365 -extensions v3_req -extfile "$CONFIG_FILE"

# Gerar chave privada do cliente
echo "👤 Gerando chave privada do cliente..."
openssl genrsa -out "$CERT_DIR/client.key" 2048

# Gerar CSR do cliente
echo "📋 Gerando CSR do cliente..."
openssl req -new -key "$CERT_DIR/client.key" -out "$CERT_DIR/client.csr" -subj "/CN=MindFlow-Client/O=Development/C=BR"

# Assinar certificado do cliente
echo "✍️ Assinando certificado do cliente..."
openssl x509 -req -in "$CERT_DIR/client.csr" -CA "$CERT_DIR/ca.crt" -CAkey "$CERT_DIR/ca.key" -CAcreateserial -out "$CERT_DIR/client.crt" -days 365

# Limpar arquivos temporários
rm "$CERT_DIR/server.csr" "$CERT_DIR/client.csr" "$CERT_DIR/ca.srl"

# Definir permissões
chmod 600 "$CERT_DIR"/*.key
chmod 644 "$CERT_DIR"/*.crt

echo ""
echo "✅ Certificados gerados com sucesso!"
echo "📁 Arquivos criados em $CERT_DIR/:"
echo "   - ca.crt      (Certificado da Autoridade Certificadora)"
echo "   - server.key  (Chave privada do servidor)"
echo "   - server.crt  (Certificado do servidor)"
echo "   - client.key  (Chave privada do cliente)"
echo "   - client.crt  (Certificado do cliente)"
echo ""
echo "🔧 Para usar no MindFlow, configure as variáveis de ambiente:"
echo "   GRPC_TLS_CERT_PATH=$(pwd)/$CERT_DIR/server.crt"
echo "   GRPC_TLS_KEY_PATH=$(pwd)/$CERT_DIR/server.key"
echo "   GRPC_TLS_CA_PATH=$(pwd)/$CERT_DIR/ca.crt"
echo "   GRPC_SECURE=true"
echo ""
echo "⚠️  Estes certificados são apenas para desenvolvimento!"
