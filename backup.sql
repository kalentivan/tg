--
-- PostgreSQL database dump
--

-- Dumped from database version 14.13
-- Dumped by pg_dump version 16.4

-- Started on 2025-05-25 17:29:15

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- TOC entry 4 (class 2615 OID 2200)
-- Name: public; Type: SCHEMA; Schema: -; Owner: postgres
--

-- *not* creating schema, since initdb creates it


ALTER SCHEMA public OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 209 (class 1259 OID 338549)
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO postgres;

--
-- TOC entry 211 (class 1259 OID 338604)
-- Name: chats; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chats (
    name character varying,
    is_group boolean,
    admin_id uuid,
    id uuid NOT NULL
);


ALTER TABLE public.chats OWNER TO postgres;

--
-- TOC entry 213 (class 1259 OID 338629)
-- Name: group_members; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.group_members (
    user_id uuid NOT NULL,
    chat_id uuid NOT NULL,
    id uuid NOT NULL
);


ALTER TABLE public.group_members OWNER TO postgres;

--
-- TOC entry 215 (class 1259 OID 338663)
-- Name: message_reads; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.message_reads (
    message_id uuid NOT NULL,
    user_id uuid NOT NULL,
    read_at timestamp without time zone,
    id uuid NOT NULL
);


ALTER TABLE public.message_reads OWNER TO postgres;

--
-- TOC entry 214 (class 1259 OID 338645)
-- Name: messages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.messages (
    chat_id uuid,
    sender_id uuid,
    text text,
    "timestamp" timestamp without time zone,
    is_read boolean,
    id uuid NOT NULL
);


ALTER TABLE public.messages OWNER TO postgres;

--
-- TOC entry 212 (class 1259 OID 338617)
-- Name: tokens; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tokens (
    jti uuid NOT NULL,
    user_id uuid NOT NULL,
    device_id character varying NOT NULL,
    revoked boolean,
    expired_time integer
);


ALTER TABLE public.tokens OWNER TO postgres;

--
-- TOC entry 210 (class 1259 OID 338594)
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    username character varying,
    email character varying,
    is_admin boolean,
    password character varying,
    id uuid NOT NULL
);


ALTER TABLE public.users OWNER TO postgres;

--
-- TOC entry 3355 (class 0 OID 338549)
-- Dependencies: 209
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.alembic_version (version_num) FROM stdin;
e47cb65b866b
\.


--
-- TOC entry 3357 (class 0 OID 338604)
-- Dependencies: 211
-- Data for Name: chats; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.chats (name, is_group, admin_id, id) FROM stdin;
\.


--
-- TOC entry 3359 (class 0 OID 338629)
-- Dependencies: 213
-- Data for Name: group_members; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.group_members (user_id, chat_id, id) FROM stdin;
\.


--
-- TOC entry 3361 (class 0 OID 338663)
-- Dependencies: 215
-- Data for Name: message_reads; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.message_reads (message_id, user_id, read_at, id) FROM stdin;
\.


--
-- TOC entry 3360 (class 0 OID 338645)
-- Dependencies: 214
-- Data for Name: messages; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.messages (chat_id, sender_id, text, "timestamp", is_read, id) FROM stdin;
\.


--
-- TOC entry 3358 (class 0 OID 338617)
-- Dependencies: 212
-- Data for Name: tokens; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.tokens (jti, user_id, device_id, revoked, expired_time) FROM stdin;
\.


--
-- TOC entry 3356 (class 0 OID 338594)
-- Dependencies: 210
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (username, email, is_admin, password, id) FROM stdin;
\.


--
-- TOC entry 3188 (class 2606 OID 338553)
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- TOC entry 3195 (class 2606 OID 338610)
-- Name: chats chats_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chats
    ADD CONSTRAINT chats_pkey PRIMARY KEY (id);


--
-- TOC entry 3200 (class 2606 OID 338633)
-- Name: group_members group_members_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_members
    ADD CONSTRAINT group_members_pkey PRIMARY KEY (user_id, chat_id, id);


--
-- TOC entry 3207 (class 2606 OID 338667)
-- Name: message_reads message_reads_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.message_reads
    ADD CONSTRAINT message_reads_pkey PRIMARY KEY (message_id, user_id, id);


--
-- TOC entry 3204 (class 2606 OID 338651)
-- Name: messages messages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_pkey PRIMARY KEY (id);


--
-- TOC entry 3198 (class 2606 OID 338623)
-- Name: tokens tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tokens
    ADD CONSTRAINT tokens_pkey PRIMARY KEY (jti);


--
-- TOC entry 3193 (class 2606 OID 338600)
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- TOC entry 3196 (class 1259 OID 338616)
-- Name: ix_chats_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_chats_id ON public.chats USING btree (id);


--
-- TOC entry 3201 (class 1259 OID 338644)
-- Name: ix_group_members_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_group_members_id ON public.group_members USING btree (id);


--
-- TOC entry 3205 (class 1259 OID 338678)
-- Name: ix_message_reads_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_message_reads_id ON public.message_reads USING btree (id);


--
-- TOC entry 3202 (class 1259 OID 338662)
-- Name: ix_messages_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_messages_id ON public.messages USING btree (id);


--
-- TOC entry 3189 (class 1259 OID 338601)
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- TOC entry 3190 (class 1259 OID 338602)
-- Name: ix_users_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_id ON public.users USING btree (id);


--
-- TOC entry 3191 (class 1259 OID 338603)
-- Name: ix_users_username; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_username ON public.users USING btree (username);


--
-- TOC entry 3208 (class 2606 OID 338611)
-- Name: chats chats_admin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chats
    ADD CONSTRAINT chats_admin_id_fkey FOREIGN KEY (admin_id) REFERENCES public.users(id);


--
-- TOC entry 3210 (class 2606 OID 338634)
-- Name: group_members group_members_chat_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_members
    ADD CONSTRAINT group_members_chat_id_fkey FOREIGN KEY (chat_id) REFERENCES public.chats(id);


--
-- TOC entry 3211 (class 2606 OID 338639)
-- Name: group_members group_members_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_members
    ADD CONSTRAINT group_members_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- TOC entry 3214 (class 2606 OID 338668)
-- Name: message_reads message_reads_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.message_reads
    ADD CONSTRAINT message_reads_message_id_fkey FOREIGN KEY (message_id) REFERENCES public.messages(id);


--
-- TOC entry 3215 (class 2606 OID 338673)
-- Name: message_reads message_reads_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.message_reads
    ADD CONSTRAINT message_reads_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- TOC entry 3212 (class 2606 OID 338652)
-- Name: messages messages_chat_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_chat_id_fkey FOREIGN KEY (chat_id) REFERENCES public.chats(id);


--
-- TOC entry 3213 (class 2606 OID 338657)
-- Name: messages messages_sender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_sender_id_fkey FOREIGN KEY (sender_id) REFERENCES public.users(id);


--
-- TOC entry 3209 (class 2606 OID 338624)
-- Name: tokens tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tokens
    ADD CONSTRAINT tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 3367 (class 0 OID 0)
-- Dependencies: 4
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE USAGE ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO PUBLIC;


-- Completed on 2025-05-25 17:29:16

--
-- PostgreSQL database dump complete
--

