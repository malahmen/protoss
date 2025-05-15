# Declare all arguments together to prevent Docker issues
ARG NODE_IMAGE
ARG NGINX_IMAGE

# Set up the Node.js environment for the frontend
FROM ${NODE_IMAGE} AS builder

# Set the working directory for the build process
WORKDIR /carrier

# Copy package.json and install dependencies
COPY package*.json ./
RUN npm install

# Copy the rest of the frontend source code
COPY . .

# Build the frontend (assuming React or similar framework)
RUN npm run build

# Set up NGINX to serve the built frontend
FROM ${NGINX_IMAGE} AS nginx

# Copy built frontend files from the previous stage
COPY --from=builder /carrier/dist /usr/share/nginx/html

# Expose the frontend port (mapped to $FRONTEND_PORT)
EXPOSE ${FRONTEND_PORT}
EXPOSE ${NGINX_PORT}

# Default NGINX config (can be customized based on your needs)
#COPY ./nginx.conf /etc/nginx/nginx.conf

# Start NGINX to serve the frontend
CMD ["nginx", "-g", "daemon off;"]
