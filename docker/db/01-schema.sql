BEGIN;
CREATE EXTENSION vector;
CREATE TABLE "user" (
 id bigserial PRIMARY KEY, email varchar(254) NOT NULL UNIQUE, provider varchar(20) NOT NULL,
 password_hash text, provider_user_id text, status varchar(30) NOT NULL,
 created_at timestamp NOT NULL, updated_at timestamp NOT NULL, UNIQUE(provider, provider_user_id)
);
CREATE TABLE product (
 product_id bigserial PRIMARY KEY, product_name text NOT NULL, description text NOT NULL,
 brand text, category text NOT NULL, price bigint NOT NULL, stock_quantity bigint NOT NULL,
 image_url text NOT NULL, status text NOT NULL, created_at timestamp NOT NULL, updated_at timestamp NOT NULL
);
CREATE TABLE cart (
 id bigserial PRIMARY KEY, user_id bigint NOT NULL UNIQUE REFERENCES "user",
 created_at timestamp NOT NULL, updated_at timestamp NOT NULL
);
CREATE TABLE cart_item (
 cart_item_id bigserial PRIMARY KEY, cart_id bigint NOT NULL REFERENCES cart,
 product_id bigint NOT NULL REFERENCES product, quantity int NOT NULL,
 created_at timestamp NOT NULL, updated_at timestamp NOT NULL, UNIQUE(cart_id, product_id)
);
CREATE TABLE wishlist (
 id bigserial PRIMARY KEY, user_id bigint NOT NULL REFERENCES "user",
 product_id bigint NOT NULL REFERENCES product, UNIQUE(user_id, product_id)
);
CREATE TABLE orders (
 order_id bigserial PRIMARY KEY, member_id bigint NOT NULL REFERENCES "user",
 order_status text NOT NULL, order_datetime timestamp NOT NULL, is_deleted boolean NOT NULL,
 recipient_name text NOT NULL, recipient_phone text NOT NULL, postal_code text NOT NULL,
 address text NOT NULL, address_detail text, shipping_fee bigint NOT NULL, total_amount bigint NOT NULL
);
CREATE TABLE payments (
 id bigserial PRIMARY KEY, order_id bigint UNIQUE NOT NULL REFERENCES orders,
 member_id bigint NOT NULL REFERENCES "user", amount bigint NOT NULL, status text NOT NULL,
 payment_key text, approved_at timestamp, canceled_at timestamp, cancel_reason text,
 created_at timestamp NOT NULL, updated_at timestamp NOT NULL
);
CREATE TABLE product_embedding (
 product_id bigint PRIMARY KEY REFERENCES product ON DELETE CASCADE, embedding vector(384) NOT NULL,
 model_name text NOT NULL, updated_at timestamptz NOT NULL DEFAULT now()
);
COMMIT;
