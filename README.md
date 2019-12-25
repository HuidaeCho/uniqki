# Uniqki

A Personal Wiki Builder <<https://uniqki.isnew.info>>

Uniqki is a simple yet powerful Perl script that can build a website with
static HTML files. Its name originated from Unique Wiki. There are two types of
pages including non-wiki and wiki pages. Only admins can create or edit
non-wiki pages while visitors or non-admin users can contriute their contents
to wiki pages depending on write access control settings. The key difference
between the two page types is that non-wiki pages can embed Perl code in page
source while wiki pages cannot.

Uniqki can be used to create a private and closed website using the web
server's rewrite rules. Since HTML files are generated by the script and
directly served by the web server, it's the server's responsibility to secure
those files and redirect requests to the script.

In a portable Perl environment like [the Strawberry Perl Portable
edition](http://strawberryperl.com), Uniqki can be self-served by itself using
an embedded web server.

It works with [the Uniqki Presenter](https://github.com/HuidaeCho/uniqki-presenter) to make presentation slides.

## License

Copyright (C) 2007-2008, 2010-2011, 2016-2019, Huidae Cho <<https://idea.isnew.info>>
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:

1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
SUCH DAMAGE.
